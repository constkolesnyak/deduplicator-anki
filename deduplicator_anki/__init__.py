import json
import os
from collections import defaultdict
from typing import Dict, List, Optional, Set, Tuple

from aqt import mw
from aqt.qt import *
from aqt.utils import showInfo

COMBINE_ALL_OPTION = "Combine All Keys"
DEFAULT_TAG_NAME = "duplicate-card"
CONFIG_FILE_NAME = "config.json"
DEFAULT_CONFIG = {
    "ankiFilter": "",
    "dedupKey": COMBINE_ALL_OPTION,
    "tagName": DEFAULT_TAG_NAME,
}


class DuplicateTaggerWindow(QWidget):
    """Main window for configuring duplicate card tagging."""

    COMBINE_ALL = COMBINE_ALL_OPTION

    def keyPressEvent(self, event):
        """Handle keyboard shortcuts."""
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self._on_ok()
        elif event.key() == Qt.Key.Key_Escape:
            self.close()
        elif event.key() == Qt.Key.Key_W and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            self.close()
        else:
            super().keyPressEvent(event)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Deduplicator")

        # State
        config = self._load_config()
        self.anki_filter = config.get('ankiFilter', '')
        self.selected_key = config.get('dedupKey', self.COMBINE_ALL)
        self.tag_name = config.get('tagName', DEFAULT_TAG_NAME)
        self.field_names: Set[str] = set()

        # UI components
        self.filter_input = QLineEdit()
        self.key_combo = QComboBox()
        self.tag_input = QLineEdit()
        self.ok_btn = None

        self._setup_ui()
        self._connect_signals()
        self._initialize_values()

    def _get_config_path(self) -> str:
        """Get the path to config.json in the Anki addons directory."""
        addon_dir = os.path.join(mw.pm.addonFolder(), 'deduplicator_anki')
        os.makedirs(addon_dir, exist_ok=True)
        return os.path.join(addon_dir, CONFIG_FILE_NAME)

    def _load_config(self) -> Dict:
        """Load configuration from config.json. Includes fallback for older keys."""
        config_path = self._get_config_path()
        config = DEFAULT_CONFIG.copy()

        try:
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                    if isinstance(loaded, dict):
                        config.update({k: v for k, v in loaded.items() if k in config})
                        # Backwards compatibility with older config keys
                        if 'selectedKey' in loaded and 'dedupKey' not in loaded:
                            config['dedupKey'] = loaded['selectedKey']
                        if 'selectedMethod' in loaded and 'tagName' not in loaded:
                            config['tagName'] = DEFAULT_TAG_NAME
        except Exception as e:
            showInfo(f'Error loading config: {e}')

        # Guard empty or invalid values
        if not config.get('tagName'):
            config['tagName'] = DEFAULT_TAG_NAME
        if not config.get('dedupKey'):
            config['dedupKey'] = self.COMBINE_ALL

        return config

    def _save_config(self) -> None:
        """Save current configuration to config.json."""
        config = {
            'ankiFilter': self.anki_filter,
            'dedupKey': self.selected_key,
            'tagName': self.tag_name or DEFAULT_TAG_NAME,
        }

        config_path = self._get_config_path()
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            showInfo(f'Error saving config: {e}')

    def _setup_ui(self) -> None:
        """Set up the user interface layout."""
        layout = QVBoxLayout()

        # Form layout for inputs
        form_layout = QFormLayout()

        # Set minimum width for all input fields
        min_width = 300

        # Filter input
        self.filter_input.setPlaceholderText('e.g., deck:MyDeck')
        self.filter_input.setMinimumWidth(min_width)
        form_layout.addRow("Filter:", self.filter_input)

        # Key selection
        self.key_combo.setMinimumWidth(min_width)
        self.key_combo.addItem(self.COMBINE_ALL)
        form_layout.addRow("Key field:", self.key_combo)

        # Tag name
        self.tag_input.setPlaceholderText(DEFAULT_TAG_NAME)
        self.tag_input.setMinimumWidth(min_width)
        form_layout.addRow("Tag:", self.tag_input)

        layout.addLayout(form_layout)

        # Button layout
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.ok_btn = QPushButton("OK")
        self.ok_btn.clicked.connect(self._on_ok)
        self.ok_btn.setDefault(True)
        self.ok_btn.setAutoDefault(True)
        button_layout.addWidget(self.ok_btn)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.close)
        button_layout.addWidget(cancel_btn)

        layout.addLayout(button_layout)

        self.setLayout(layout)

    def _connect_signals(self) -> None:
        """Connect UI signals to handlers."""
        self.filter_input.textChanged.connect(self._on_filter_changed)
        self.filter_input.editingFinished.connect(self._on_filter_finished)
        self.key_combo.currentIndexChanged.connect(self._on_key_changed_index)
        self.tag_input.editingFinished.connect(self._on_tag_changed)
        self.tag_input.textChanged.connect(self._on_tag_changed_live)

    def _initialize_values(self) -> None:
        """Initialize UI with saved values."""
        # Block signals during initialization to prevent premature saves
        self.filter_input.blockSignals(True)
        self.key_combo.blockSignals(True)
        self.tag_input.blockSignals(True)

        self.filter_input.setText(self.anki_filter)

        # Update field list and restore selected key
        if self.anki_filter:
            self._update_field_list()
        else:
            # Even without a filter, ensure the key combo has the default option
            if self.key_combo.count() == 0:
                self.key_combo.addItem(self.COMBINE_ALL)
            self.key_combo.setCurrentText(self.COMBINE_ALL)

        # Restore tag name
        self.tag_input.setText(self.tag_name)

        # Re-enable signals
        self.filter_input.blockSignals(False)
        self.key_combo.blockSignals(False)
        self.tag_input.blockSignals(False)

        # Focus the filter field to allow quick keyboard workflow
        self.filter_input.setFocus()

    def _on_filter_changed(self, text: str) -> None:
        """Handle filter text changes."""
        self.anki_filter = text

    def _on_filter_finished(self) -> None:
        """Handle filter editing finished."""
        self._save_config()
        self._update_field_list()

    def _on_key_changed_index(self, index: int) -> None:
        """Handle key selection change by index."""
        if index >= 0:
            self.selected_key = self.key_combo.currentText()
            self._save_config()

    def _on_tag_changed_live(self, text: str) -> None:
        """Update tag name as the user types."""
        self.tag_name = text.strip()

    def _on_tag_changed(self) -> None:
        """Persist tag name changes."""
        self.tag_name = self.tag_name or DEFAULT_TAG_NAME
        self.tag_input.setText(self.tag_name)
        self._save_config()

    def _update_field_list(self) -> None:
        """Update the field list based on current filter."""
        if not self.anki_filter:
            return

        try:
            note_ids = mw.col.findNotes(self.anki_filter)
        except Exception as e:
            showInfo(f'Invalid Anki filter syntax: {e}')
            return

        # Get field names
        self.field_names.clear()
        field_names_method = getattr(mw.col, "field_names_for_note_ids", None)

        if callable(field_names_method):
            self.field_names.update(field_names_method(note_ids))
        else:
            # Fallback for older Anki versions
            for note_id in note_ids[:100]:  # Limit to first 100 for performance
                note = mw.col.getNote(note_id)
                self.field_names.update(note.keys())

        # Update combo box
        # Block signals to prevent triggering save during update
        self.key_combo.blockSignals(True)
        self.key_combo.clear()
        self.key_combo.addItem(self.COMBINE_ALL)
        for field in sorted(self.field_names):
            self.key_combo.addItem(field)

        # Restore selection if valid
        if self.selected_key in self.field_names or self.selected_key == self.COMBINE_ALL:
            self.key_combo.setCurrentText(self.selected_key)
        else:
            self.selected_key = self.COMBINE_ALL
            self.key_combo.setCurrentText(self.COMBINE_ALL)

        self.key_combo.blockSignals(False)

    def _on_ok(self) -> None:
        """Handle OK button click - tag duplicates and close."""
        if not self.anki_filter:
            showInfo('No Anki filter specified')
            return

        tagged = self._tag_duplicates()
        if tagged is not None:
            showInfo(tagged)
            self.close()

    def _get_dedup_key(self, note) -> Tuple:
        """Get the deduplication key for a note."""
        if self.selected_key == self.COMBINE_ALL:
            return tuple(note.values())

        if self.selected_key in note.keys():
            idx = note.keys().index(self.selected_key)
            return (note.values()[idx],)

        return None

    def _collect_note_ids(self) -> Optional[List[int]]:
        """Return note ids for the configured filter."""
        try:
            return mw.col.findNotes(self.anki_filter)
        except Exception as e:
            showInfo(f'Error executing filter: {e}')
            return None

    def _tag_duplicates(self) -> Optional[str]:
        """Find and tag all duplicate notes."""
        note_ids = self._collect_note_ids()
        if note_ids is None:
            return None

        try:
            duplicates = self._group_duplicates(note_ids)
        except Exception as e:
            showInfo(f'Error while locating duplicates: {e}')
            return None

        tag_to_apply = self.tag_name or DEFAULT_TAG_NAME
        total_tagged, details = self._apply_tag_to_duplicates(duplicates, tag_to_apply)

        message = f"Total: {total_tagged} notes tagged as '{tag_to_apply}'"
        # if details:
        #     message += "\n\n" + "\n".join(details)
        #     if total_tagged > len(details):
        #         message += "\n..."

        mw.reset()
        return message

    def _group_duplicates(self, note_ids: List[int]) -> Dict[Tuple, List[int]]:
        """Return a mapping of dedup keys to note ids."""
        duplicates: Dict[Tuple, List[int]] = defaultdict(list)

        for note_id in note_ids:
            note = mw.col.getNote(note_id)

            if not note.cards():
                continue

            dedup_key = self._get_dedup_key(note)
            if dedup_key is None:
                continue

            duplicates[dedup_key].append(note_id)

        return duplicates

    def _apply_tag_to_duplicates(
        self, duplicates: Dict[Tuple, List[int]], tag_to_apply: str
    ) -> Tuple[int, List[str]]:
        """Apply the provided tag to duplicates and build a summary."""
        total_tagged = 0
        details: List[str] = []
        max_details = 50

        for key, note_ids_list in duplicates.items():
            if len(note_ids_list) <= 1:
                continue

            # Format key for display
            key_display = "(combined keys)" if self.selected_key == self.COMBINE_ALL else str(key[0])

            note_ids_list_sorted = sorted(note_ids_list)
            # Keep the first note (oldest by id) untagged to serve as the canonical entry
            for note_id in note_ids_list_sorted[1:]:
                note = mw.col.getNote(note_id)
                note.addTag(tag_to_apply)
                note.flush()
                total_tagged += 1
                if len(details) < max_details:
                    details.append(f"{key_display}: note_id:{note_id} [TAGGED]")

        return total_tagged, details


def show_window() -> None:
    """Display the duplicate tagging configuration window."""
    mw.duplicateTaggerWindow = DuplicateTaggerWindow()
    mw.duplicateTaggerWindow.show()


# Add menu item to Tools menu
action = QAction("Deduplicate", mw)
action.triggered.connect(show_window)
mw.form.menuTools.addAction(action)
