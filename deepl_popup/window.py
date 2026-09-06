import subprocess
import threading

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gdk, GLib, Gtk  # noqa: E402

from deepl_popup import api, config, languages


def _error_message(error) -> str:
    if isinstance(error, api.AuthError):
        return f"Invalid API key — check {config.CONFIG_PATH}"
    if isinstance(error, api.QuotaExceededError):
        return "Translation quota exceeded for this month"
    if isinstance(error, api.RateLimitError):
        return "Rate limited, try again in a moment"
    if isinstance(error, api.NetworkError):
        return "Network error — check your connection"
    return str(error)[:200]


class PopupWindow(Gtk.Window):
    def __init__(self):
        super().__init__(title="DeepL Popup Translator")
        self.set_default_size(700, 400)
        self.set_position(Gtk.WindowPosition.CENTER)

        self.config = config.load()
        self.last_detected_source = None
        self.request_generation = 0

        self.connect("delete-event", self._on_delete_event)
        self.connect("key-press-event", self._on_key_press)

        self.stack = Gtk.Stack()
        self.add(self.stack)

        self.stack.add_named(self._build_setup_page(), "setup")
        self.stack.add_named(self._build_translate_page(), "translate")

        self._populate_language_combos()

        # Build and realize the whole widget tree now, then hide — so the
        # first `present_with_time()` on a hotkey press is instant and the
        # window isn't left blank (present() assumes show() already ran once).
        self.show_all()
        self.hide()

    # ---- setup page (shown when no API key is configured yet) ----

    def _build_setup_page(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.set_margin_top(24)
        box.set_margin_bottom(24)
        box.set_margin_start(24)
        box.set_margin_end(24)

        label = Gtk.Label(label="Enter your DeepL API key to get started:")
        label.set_halign(Gtk.Align.START)
        box.pack_start(label, False, False, 0)

        self.setup_entry = Gtk.Entry()
        self.setup_entry.set_visibility(False)
        self.setup_entry.set_placeholder_text("xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx:fx")
        self.setup_entry.connect("activate", lambda *_: self._on_setup_save_clicked())
        box.pack_start(self.setup_entry, False, False, 0)

        self.setup_error_label = Gtk.Label(label="")
        self.setup_error_label.set_halign(Gtk.Align.START)
        self.setup_error_label.get_style_context().add_class("error")
        box.pack_start(self.setup_error_label, False, False, 0)

        save_button = Gtk.Button(label="Save")
        save_button.set_halign(Gtk.Align.END)
        save_button.connect("clicked", lambda *_: self._on_setup_save_clicked())
        box.pack_start(save_button, False, False, 0)

        return box

    def _on_setup_save_clicked(self):
        key = self.setup_entry.get_text().strip()
        if not key:
            self.setup_error_label.set_text("API key cannot be empty")
            return
        config.set_api_key(key)
        self.config = config.load()
        self.setup_error_label.set_text("")
        self.stack.set_visible_child_name("translate")
        self._populate_language_combos()
        GLib.idle_add(self._populate_from_clipboard)

    # ---- main translate page ----

    def _build_translate_page(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.set_margin_top(8)
        box.set_margin_bottom(8)
        box.set_margin_start(8)
        box.set_margin_end(8)

        lang_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.source_lang_combo = Gtk.ComboBoxText()
        self.swap_button = Gtk.Button.new_from_icon_name(
            "object-flip-horizontal-symbolic", Gtk.IconSize.BUTTON
        )
        self.swap_button.set_tooltip_text("Swap languages")
        self.swap_button.connect("clicked", lambda *_: self.do_swap())
        self.target_lang_combo = Gtk.ComboBoxText()
        lang_row.pack_start(self.source_lang_combo, True, True, 0)
        lang_row.pack_start(self.swap_button, False, False, 0)
        lang_row.pack_start(self.target_lang_combo, True, True, 0)
        box.pack_start(lang_row, False, False, 0)

        paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        paned.set_position(340)
        paned.set_wide_handle(True)

        self.source_buffer = Gtk.TextBuffer()
        self.source_textview = Gtk.TextView(buffer=self.source_buffer)
        self.source_textview.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        source_scroller = Gtk.ScrolledWindow()
        source_scroller.add(self.source_textview)
        paned.pack1(source_scroller, True, False)

        self.target_buffer = Gtk.TextBuffer()
        self.target_textview = Gtk.TextView(buffer=self.target_buffer)
        self.target_textview.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.target_textview.set_editable(False)
        target_scroller = Gtk.ScrolledWindow()
        target_scroller.add(self.target_textview)
        paned.pack2(target_scroller, True, False)

        box.pack_start(paned, True, True, 0)

        bottom_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        bottom_row.set_halign(Gtk.Align.END)

        self.error_label = Gtk.Label(label="")
        self.error_revealer = Gtk.Revealer()
        self.error_revealer.add(self.error_label)
        self.error_revealer.set_reveal_child(False)
        bottom_row.pack_start(self.error_revealer, True, True, 0)

        self.spinner = Gtk.Spinner()
        self.spinner.set_visible(False)
        bottom_row.pack_start(self.spinner, False, False, 0)

        self.translate_button = Gtk.Button(label="Translate")
        self.translate_button.connect("clicked", lambda *_: self.do_translate())
        bottom_row.pack_start(self.translate_button, False, False, 0)

        self.copy_button = Gtk.Button(label="Copy")
        self.copy_button.connect("clicked", lambda *_: self.do_copy())
        bottom_row.pack_start(self.copy_button, False, False, 0)

        box.pack_start(bottom_row, False, False, 0)

        return box

    # ---- language combo population ----

    def _populate_language_combos(self):
        cached_source, cached_target = config.load_language_cache()
        source_list = cached_source or languages.FALLBACK_SOURCE_LANGUAGES
        target_list = cached_target or languages.FALLBACK_TARGET_LANGUAGES
        self._fill_combo(self.source_lang_combo, source_list, "AUTO")
        self._fill_combo(self.target_lang_combo, target_list, self.config.default_target_lang)
        if cached_source is None and self.config.api_key:
            threading.Thread(target=self._fetch_languages_worker, daemon=True).start()

    def _fetch_languages_worker(self):
        try:
            src = api.get_languages("source", self.config.api_key)
            tgt = api.get_languages("target", self.config.api_key)
        except api.DeepLError:
            return
        src = [{"language": "AUTO", "name": "Detect language"}] + src
        config.save_language_cache(src, tgt)
        GLib.idle_add(self._on_languages_fetched, src, tgt)

    def _on_languages_fetched(self, source_list, target_list):
        prev_source = self.source_lang_combo.get_active_id() or "AUTO"
        prev_target = self.target_lang_combo.get_active_id() or self.config.default_target_lang
        self._fill_combo(self.source_lang_combo, source_list, prev_source)
        self._fill_combo(self.target_lang_combo, target_list, prev_target)
        return False

    def _fill_combo(self, combo, lang_list, default_id):
        combo.remove_all()
        for row in lang_list:
            combo.append(row["language"], row["name"])
        if not combo.set_active_id(default_id):
            combo.set_active(0)

    # ---- show/hide flow ----

    def on_show_requested(self):
        if self.config.api_key:
            self.stack.set_visible_child_name("translate")
            self.present_with_time(Gdk.CURRENT_TIME)
            GLib.idle_add(self._populate_from_clipboard)
        else:
            self.stack.set_visible_child_name("setup")
            self.present_with_time(Gdk.CURRENT_TIME)
        return False

    def _populate_from_clipboard(self):
        clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        text = clipboard.wait_for_text()
        if not text:
            try:
                proc = subprocess.run(
                    ["wl-paste", "-n"], capture_output=True, text=True, timeout=1
                )
                text = proc.stdout
            except (FileNotFoundError, subprocess.TimeoutExpired):
                text = ""
        self.source_buffer.set_text(text or "")
        self.source_textview.grab_focus()
        self.source_buffer.place_cursor(self.source_buffer.get_end_iter())
        if text and text.strip():
            self.do_translate()
        return False

    def _on_delete_event(self, widget, event):
        self.hide()
        return True

    def _on_key_press(self, widget, event):
        if event.keyval == Gdk.KEY_Escape:
            self.hide()
            return True
        if event.keyval in (Gdk.KEY_Return, Gdk.KEY_KP_Enter) and (
            event.state & Gdk.ModifierType.CONTROL_MASK
        ):
            self.do_translate()
            return True
        return False

    # ---- text helpers ----

    def _get_source_text(self):
        start, end = self.source_buffer.get_bounds()
        return self.source_buffer.get_text(start, end, False)

    def _get_target_text(self):
        start, end = self.target_buffer.get_bounds()
        return self.target_buffer.get_text(start, end, False)

    # ---- actions ----

    def do_translate(self):
        text = self._get_source_text()
        if not text.strip():
            return
        source_id = self.source_lang_combo.get_active_id()
        target_id = self.target_lang_combo.get_active_id()
        source_lang = None if source_id in (None, "AUTO") else source_id

        self.request_generation += 1
        gen = self.request_generation
        self._set_busy(True)
        api_key = self.config.api_key

        def worker():
            try:
                result = api.translate(text, target_id, source_lang=source_lang, api_key=api_key)
                GLib.idle_add(self._on_translate_done, gen, result, None)
            except api.DeepLError as e:
                GLib.idle_add(self._on_translate_done, gen, None, e)

        threading.Thread(target=worker, daemon=True).start()

    def _on_translate_done(self, gen, result, error):
        if gen != self.request_generation:
            return False
        self._set_busy(False)
        if error is not None:
            self._show_error(error)
            return False
        self.target_buffer.set_text(result.text)
        self.last_detected_source = result.detected_source_language
        self._clear_error()
        return False

    def do_swap(self):
        source_id = self.source_lang_combo.get_active_id()
        target_id = self.target_lang_combo.get_active_id()

        if source_id == "AUTO":
            if not self.last_detected_source:
                return
            effective_source = self.last_detected_source
        else:
            effective_source = source_id

        new_target = languages.to_target_code(effective_source, self.config.preferred_variants)
        new_source = languages.to_source_code(target_id)

        src_text = self._get_source_text()
        tgt_text = self._get_target_text()
        self.source_buffer.set_text(tgt_text)
        self.target_buffer.set_text(src_text)

        self.source_lang_combo.set_active_id(new_source)
        self.target_lang_combo.set_active_id(new_target)
        self.last_detected_source = None

    def do_copy(self):
        text = self._get_target_text()
        if not text:
            return
        clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        clipboard.set_text(text, -1)
        clipboard.store()

    # ---- busy/error UI ----

    def _set_busy(self, busy):
        self.spinner.set_visible(busy)
        if busy:
            self.spinner.start()
        else:
            self.spinner.stop()
        self.translate_button.set_sensitive(not busy)

    def _show_error(self, error):
        self.error_label.set_text(_error_message(error))
        self.error_revealer.set_reveal_child(True)

    def _clear_error(self):
        self.error_revealer.set_reveal_child(False)
