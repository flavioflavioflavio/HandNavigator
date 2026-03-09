# MIT License — Copyright (c) 2026 Flávio Takemoto
# See LICENSE file for full terms.

"""
HandNavigator — Internationalization Module

Provides centralized string tables for en, pt-BR, and es.
Detects the OS locale automatically and falls back to English.

Usage:
    from ui.i18n import t
    label = t("window_title")
"""

import locale
from typing import Dict

# ─── String Tables ───────────────────────────────────────────────────────────

_STRINGS: Dict[str, Dict[str, str]] = {
    "en": {
        # Window
        "window_title":       "HandNavigator — Virtual 3D Mouse",
        "app_name":           "HandNavigator",

        # Status bar
        "reset_camera":       "Reset Camera",
        "reset_camera_tip":   "Reset camera to default (Ctrl+R)",
        "mode_preview":       "Mode: Preview",
        "mode_live":          "Mode: Live",
        "profile_label":      "Profile: {name}",

        # Tray close notification
        "tray_minimized":     "Running in background. Right-click tray icon to quit.",

        # Tray menu
        "tray_show_viewport": "Show 3D Viewport",
        "tray_toggle_pip":    "Show/Hide PIP",
        "tray_menu_mode":     "Mode",
        "tray_mode_preview":  "Preview (3D Viewport)",
        "tray_mode_live":     "Live (Send to App)",
        "tray_menu_profile":  "Profile",
        "tray_quit":          "Quit HandNavigator",

        # Tray tooltip
        "tray_tooltip":       "HandNavigator — {gesture}",

        # Gestures
        "gesture_idle":       "Idle",
        "gesture_pan":        "Pan",
        "gesture_zoom":       "Zoom",
        "gesture_orbit":      "Orbit",

        # Gesture status bar labels (with emoji)
        "gesture_idle_label":  "IDLE",
        "gesture_pan_label":   "PAN 🤏",
        "gesture_zoom_label":  "ZOOM 🤙",
        "gesture_orbit_label": "ORBIT ✊",
    },

    "pt-BR": {
        # Janela
        "window_title":       "HandNavigator — Mouse 3D Virtual",
        "app_name":           "HandNavigator",

        # Barra de status
        "reset_camera":       "Resetar Câmera",
        "reset_camera_tip":   "Resetar câmera para padrão (Ctrl+R)",
        "mode_preview":       "Modo: Visualização",
        "mode_live":          "Modo: Ao Vivo",
        "profile_label":      "Perfil: {name}",

        # Notificação ao minimizar
        "tray_minimized":     "Rodando em segundo plano. Clique com o botão direito no ícone para sair.",

        # Menu da bandeja
        "tray_show_viewport": "Mostrar Viewport 3D",
        "tray_toggle_pip":    "Mostrar/Ocultar PIP",
        "tray_menu_mode":     "Modo",
        "tray_mode_preview":  "Visualização (Viewport 3D)",
        "tray_mode_live":     "Ao Vivo (Enviar para App)",
        "tray_menu_profile":  "Perfil",
        "tray_quit":          "Sair do HandNavigator",

        # Tooltip da bandeja
        "tray_tooltip":       "HandNavigator — {gesture}",

        # Gestos
        "gesture_idle":       "Parado",
        "gesture_pan":        "Pan",
        "gesture_zoom":       "Zoom",
        "gesture_orbit":      "Órbita",

        # Labels na barra de status (com emoji)
        "gesture_idle_label":  "PARADO",
        "gesture_pan_label":   "PAN 🤏",
        "gesture_zoom_label":  "ZOOM 🤙",
        "gesture_orbit_label": "ÓRBITA ✊",
    },

    "es": {
        # Ventana
        "window_title":       "HandNavigator — Ratón 3D Virtual",
        "app_name":           "HandNavigator",

        # Barra de estado
        "reset_camera":       "Resetear Cámara",
        "reset_camera_tip":   "Resetear cámara a valores por defecto (Ctrl+R)",
        "mode_preview":       "Modo: Vista Previa",
        "mode_live":          "Modo: En Vivo",
        "profile_label":      "Perfil: {name}",

        # Notificación al minimizar
        "tray_minimized":     "Ejecutándose en segundo plano. Clic derecho en el ícono para salir.",

        # Menú de bandeja
        "tray_show_viewport": "Mostrar Viewport 3D",
        "tray_toggle_pip":    "Mostrar/Ocultar PIP",
        "tray_menu_mode":     "Modo",
        "tray_mode_preview":  "Vista Previa (Viewport 3D)",
        "tray_mode_live":     "En Vivo (Enviar a App)",
        "tray_menu_profile":  "Perfil",
        "tray_quit":          "Salir de HandNavigator",

        # Tooltip de bandeja
        "tray_tooltip":       "HandNavigator — {gesture}",

        # Gestos
        "gesture_idle":       "Inactivo",
        "gesture_pan":        "Pan",
        "gesture_zoom":       "Zoom",
        "gesture_orbit":      "Órbita",

        # Labels en barra de estado (con emoji)
        "gesture_idle_label":  "INACTIVO",
        "gesture_pan_label":   "PAN 🤏",
        "gesture_zoom_label":  "ZOOM 🤙",
        "gesture_orbit_label": "ÓRBITA ✊",
    },
}


# ─── Locale Detection ───────────────────────────────────────────────────────

_LOCALE_MAP = {
    "pt": "pt-BR",
    "pt_br": "pt-BR",
    "es": "es",
    "es_es": "es",
    "es_mx": "es",
    "es_ar": "es",
}

_active_locale: str = "en"


def _detect_locale() -> str:
    """Detect the OS locale and map to our supported locales."""
    try:
        system_locale, _ = locale.getdefaultlocale()
        if system_locale:
            code = system_locale.lower().replace("-", "_")
            # Try full match first (pt_br), then language-only (pt)
            if code in _LOCALE_MAP:
                return _LOCALE_MAP[code]
            lang = code.split("_")[0]
            if lang in _LOCALE_MAP:
                return _LOCALE_MAP[lang]
    except Exception:
        pass
    return "en"


def init_locale(override: str = "") -> None:
    """
    Initialize the active locale.

    Parameters
    ----------
    override : str
        Force a specific locale (e.g., "pt-BR"). Empty = auto-detect.
    """
    global _active_locale
    if override and override in _STRINGS:
        _active_locale = override
    else:
        _active_locale = _detect_locale()


def get_locale() -> str:
    """Return the currently active locale key."""
    return _active_locale


def t(key: str, **kwargs) -> str:
    """
    Translate a string key using the active locale.

    Falls back to English if key is missing in the active locale.

    Parameters
    ----------
    key : str
        The translation key (e.g., "window_title").
    **kwargs
        Format arguments (e.g., t("profile_label", name="Cinema 4D")).
    """
    table = _STRINGS.get(_active_locale, _STRINGS["en"])
    text = table.get(key, _STRINGS["en"].get(key, key))
    if kwargs:
        text = text.format(**kwargs)
    return text


# Auto-detect on import
init_locale()
