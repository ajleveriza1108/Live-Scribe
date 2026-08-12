from pathlib import Path


SOURCE = Path("src/taglish_transcriber/ui.py").read_text(encoding="utf-8")
MODELS_SECTION = SOURCE.split("    def _build_models_page(self) -> None:", 1)[1].split(
    "    def _build_settings_page(self) -> None:", 1
)[0]


def test_models_page_uses_full_page_scroll_container():
    assert "page.grid_rowconfigure(0, weight=1)" in MODELS_SECTION
    assert "models_scroll = ctk.CTkScrollableFrame(" in MODELS_SECTION
    assert "models_scroll.grid(row=0, column=0, sticky=\"nsew\")" in MODELS_SECTION
    assert "self.models_scroll_frame = models_scroll" in MODELS_SECTION


def test_all_models_cards_live_inside_scroll_container():
    assert 'header = ctk.CTkFrame(models_scroll, fg_color="transparent")' in MODELS_SECTION
    assert "hardware_card = self._card(models_scroll" in MODELS_SECTION
    assert "choose_card = self._card(models_scroll" in MODELS_SECTION
    assert "models_scroll, row=3, column=0" in MODELS_SECTION
    assert "models_scroll, row=4, column=0" in MODELS_SECTION


def test_download_button_has_real_model_buttons_parent():
    assert (
        "self.download_model_button = ctk.CTkButton(\n"
        "            model_buttons,"
    ) in MODELS_SECTION
    assert "in_=model_buttons" not in MODELS_SECTION
    assert 'text="Download Selected Quality"' in MODELS_SECTION
