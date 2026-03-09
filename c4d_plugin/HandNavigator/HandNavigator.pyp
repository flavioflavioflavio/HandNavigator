# MIT License — Copyright (c) 2026 Flavio
# See LICENSE file for full terms.

"""
HandNavigator — Cinema 4D Plugin

Receives UDP navigation commands from the HandNavigator desktop app
and applies them to the active viewport camera. Supports orbit, pan,
and zoom with adjustable sensitivity via an integrated dashboard.

Installation:
  C4D → Edit > Preferences > Plugins → Add Folder → select this folder.
  Restart C4D. Access via Extensions > HandNavigator.

Protocol:
  JSON over UDP on localhost. See README.md for command reference.
"""

import c4d
import json
import math
import socket


# ─── Plugin Identity ─────────────────────────────────────────────────────────

PLUGIN_ID = 1067724   # Official ID — registered at plugincafe.maxon.net
PLUGIN_VERSION = "1.0.0"
PLUGIN_AUTHOR = "Flávio Takemoto"
PLUGIN_WEBSITE = "http://www.takemoto.com.br"
PLUGIN_LICENSE = "MIT License"


# ─── Defaults ────────────────────────────────────────────────────────────────

DEFAULT_HOST       = "127.0.0.1"
DEFAULT_PORT       = 19700
DEFAULT_ORBIT_SENS = 100.0
DEFAULT_PAN_SENS   = 500.0
DEFAULT_ZOOM_SENS  = 1000.0
DEFAULT_TIMER_MS   = 30

# ── Slider ranges
ORBIT_MIN, ORBIT_MAX = 1, 500
PAN_MIN,   PAN_MAX   = 1, 2000
ZOOM_MIN,  ZOOM_MAX  = 1, 5000
PORT_MIN,  PORT_MAX  = 1024, 65535
POLL_MIN,  POLL_MAX  = 10, 200

# ── Pitch clamp (degrees)
PITCH_LIMIT_DEG = 85.0


# ─── i18n ────────────────────────────────────────────────────────────────────

_STRINGS = {
    "en": {
        "plugin_name":     "HandNavigator",
        "plugin_help":     "Receive hand-tracking navigation via UDP",
        "starting":        "Starting...",
        "listening":       "Listening on {host}:{port}",
        "error":           "Error: {msg}",
        "sensitivity":     "Sensitivity",
        "orbit":           "Orbit",
        "pan":             "Pan",
        "zoom":            "Zoom",
        "connection":      "Connection",
        "port":            "Port",
        "poll_ms":         "Poll (ms)",
        "reset_defaults":  "Reset Defaults",
        "reset_camera":    "Reset Camera",
        "server_stopped":  "Server stopped",
        "author_by":       "by",
        "license":         "MIT License",
    },
    "pt-BR": {
        "plugin_name":     "HandNavigator",
        "plugin_help":     "Receber navegação por rastreamento de mãos via UDP",
        "starting":        "Iniciando...",
        "listening":       "Ouvindo em {host}:{port}",
        "error":           "Erro: {msg}",
        "sensitivity":     "Sensibilidade",
        "orbit":           "Órbita",
        "pan":             "Pan",
        "zoom":            "Zoom",
        "connection":      "Conexão",
        "port":            "Porta",
        "poll_ms":         "Intervalo (ms)",
        "reset_defaults":  "Restaurar Padrões",
        "reset_camera":    "Resetar Câmera",
        "server_stopped":  "Servidor parado",
        "author_by":       "por",
        "license":         "Licença MIT",
    },
    "es": {
        "plugin_name":     "HandNavigator",
        "plugin_help":     "Recibir navegación por seguimiento de manos vía UDP",
        "starting":        "Iniciando...",
        "listening":       "Escuchando en {host}:{port}",
        "error":           "Error: {msg}",
        "sensitivity":     "Sensibilidad",
        "orbit":           "Órbita",
        "pan":             "Pan",
        "zoom":            "Zoom",
        "connection":      "Conexión",
        "port":            "Puerto",
        "poll_ms":         "Intervalo (ms)",
        "reset_defaults":  "Restaurar Valores",
        "reset_camera":    "Resetear Cámara",
        "server_stopped":  "Servidor detenido",
        "author_by":       "por",
        "license":         "Licencia MIT",
    },
}

# Map C4D language codes → our locale keys
_LANG_MAP = {
    "us": "en", "en": "en", "gb": "en",
    "br": "pt-BR", "pt": "pt-BR",
    "es": "es",
}


def _detect_locale() -> str:
    """Detect C4D's UI language and return our locale key."""
    try:
        lang_info = c4d.GeGetLanguage(c4d.LANGUAGE_CINEMA4D)
        code = lang_info.get("extensions_id", "us").lower()
        return _LANG_MAP.get(code, "en")
    except Exception:
        return "en"


def _t(key: str, **kwargs) -> str:
    """Translate a string key using the detected locale."""
    locale = _detect_locale()
    table = _STRINGS.get(locale, _STRINGS["en"])
    text = table.get(key, _STRINGS["en"].get(key, key))
    if kwargs:
        text = text.format(**kwargs)
    return text


# ─── Widget IDs ──────────────────────────────────────────────────────────────

ID_STATUS         = 10001
ID_ORBIT_SLIDER   = 10010
ID_PAN_SLIDER     = 10020
ID_ZOOM_SLIDER    = 10030
ID_PORT_INPUT     = 10040
ID_INTERVAL_INPUT = 10050
ID_BTN_DEFAULTS   = 10060
ID_BTN_RESET_CAM  = 10070

# Group IDs (non-interactive, just for layout)
GRP_STATUS        = 20001
GRP_SENSITIVITY   = 20010
GRP_CONNECTION    = 20020
GRP_BUTTONS       = 20030
GRP_ABOUT         = 20040
ID_ABOUT_NAME     = 10080
ID_ABOUT_AUTHOR   = 10081
ID_ABOUT_SITE     = 10082
ID_ABOUT_LICENSE  = 10083


# ─── Navigation Logic ───────────────────────────────────────────────────────

def _apply_orbit(cam, dx: float, dy: float) -> None:
    """
    Arc-ball orbit around the camera's current look-at point.

    Adds rotation deltas to the current HPB and repositions the camera
    on the orbit sphere. The orbit center is computed dynamically by
    projecting the origin onto the camera's look ray, so it works
    correctly after panning or zooming.
    """
    pos = cam.GetAbsPos()
    rot = cam.GetAbsRot()
    h, p = rot.x, rot.y

    # Forward direction from current HPB
    cos_h, sin_h = math.cos(h), math.sin(h)
    cos_p, sin_p = math.cos(p), math.sin(p)
    fwd_x = -sin_h * cos_p
    fwd_y = sin_p
    fwd_z = cos_h * cos_p

    # Distance to orbit center (projection of origin onto look ray)
    t = -(pos.x * fwd_x + pos.y * fwd_y + pos.z * fwd_z)
    if t < 10.0:
        t = 500.0

    # Orbit center
    tx = pos.x + fwd_x * t
    ty = pos.y + fwd_y * t
    tz = pos.z + fwd_z * t

    # Apply rotation deltas
    h += math.radians(dx)
    p -= math.radians(dy)
    pitch_limit = math.radians(PITCH_LIMIT_DEG)
    p = max(-pitch_limit, min(pitch_limit, p))

    # New forward from updated HPB
    nfx = -math.sin(h) * math.cos(p)
    nfy = math.sin(p)
    nfz = math.cos(h) * math.cos(p)

    # Reposition camera on orbit sphere
    cam.SetAbsPos(c4d.Vector(tx - nfx * t, ty - nfy * t, tz - nfz * t))
    cam.SetAbsRot(c4d.Vector(h, p, 0))


def _apply_pan(cam, dx: float, dy: float) -> None:
    """Translate camera along its local right and up axes."""
    mg = cam.GetMg()
    right = mg.v1.GetNormalized()
    up = mg.v2.GetNormalized()
    pos = cam.GetRelPos()
    pos += right * (-dx) + up * dy
    cam.SetRelPos(pos)


def _apply_zoom(cam, dz: float) -> None:
    """Move camera along its forward axis (dolly zoom)."""
    mg = cam.GetMg()
    forward = mg.v3.GetNormalized()
    pos = cam.GetRelPos()
    pos += forward * dz
    cam.SetRelPos(pos)


def _reset_camera(cam) -> None:
    """Reset camera to default position and rotation."""
    cam.SetRelPos(c4d.Vector(0, 100, -300))
    cam.SetRelRot(c4d.Vector(0, 0, 0))


# ─── Camera Helper ───────────────────────────────────────────────────────────

def _get_active_camera():
    """Return the active viewport camera, or None."""
    doc = c4d.documents.GetActiveDocument()
    if doc is None:
        return None
    bd = doc.GetActiveBaseDraw()
    if bd is None:
        return None
    cam = bd.GetSceneCamera(doc)
    if cam is None:
        cam = bd.GetEditorCamera()
    return cam


# ─── Dialog ──────────────────────────────────────────────────────────────────

class HandNavDialog(c4d.gui.GeDialog):
    """Dashboard dialog with UDP receiver and sensitivity controls."""

    def __init__(self):
        super().__init__()
        self._sock = None
        self._total = 0
        self._orbit_sens = DEFAULT_ORBIT_SENS
        self._pan_sens = DEFAULT_PAN_SENS
        self._zoom_sens = DEFAULT_ZOOM_SENS
        self._port = DEFAULT_PORT
        self._timer_ms = DEFAULT_TIMER_MS

    # ── Layout ────────────────────────────────────────────────────────────

    def CreateLayout(self):
        self.SetTitle(_t("plugin_name") + " v" + PLUGIN_VERSION)

        # Status bar
        self.GroupBegin(GRP_STATUS, c4d.BFH_SCALEFIT, cols=1)
        self.AddStaticText(ID_STATUS, c4d.BFH_SCALEFIT, name=_t("starting"))
        self.GroupEnd()

        self.AddSeparatorH(c4d.BFH_SCALEFIT)

        # Sensitivity
        self.GroupBegin(GRP_SENSITIVITY, c4d.BFH_SCALEFIT, cols=2,
                        title=_t("sensitivity"))
        self.GroupBorderSpace(8, 4, 8, 4)
        self.AddStaticText(0, c4d.BFH_LEFT, name=_t("orbit"))
        self.AddEditSlider(ID_ORBIT_SLIDER, c4d.BFH_SCALEFIT)
        self.AddStaticText(0, c4d.BFH_LEFT, name=_t("pan"))
        self.AddEditSlider(ID_PAN_SLIDER, c4d.BFH_SCALEFIT)
        self.AddStaticText(0, c4d.BFH_LEFT, name=_t("zoom"))
        self.AddEditSlider(ID_ZOOM_SLIDER, c4d.BFH_SCALEFIT)
        self.GroupEnd()

        self.AddSeparatorH(c4d.BFH_SCALEFIT)

        # Connection
        self.GroupBegin(GRP_CONNECTION, c4d.BFH_SCALEFIT, cols=2,
                        title=_t("connection"))
        self.GroupBorderSpace(8, 4, 8, 4)
        self.AddStaticText(0, c4d.BFH_LEFT, name=_t("port"))
        self.AddEditNumber(ID_PORT_INPUT, c4d.BFH_SCALEFIT)
        self.AddStaticText(0, c4d.BFH_LEFT, name=_t("poll_ms"))
        self.AddEditNumber(ID_INTERVAL_INPUT, c4d.BFH_SCALEFIT)
        self.GroupEnd()

        self.AddSeparatorH(c4d.BFH_SCALEFIT)

        # Buttons
        self.GroupBegin(GRP_BUTTONS, c4d.BFH_SCALEFIT, cols=2)
        self.AddButton(ID_BTN_DEFAULTS, c4d.BFH_SCALEFIT,
                       name=_t("reset_defaults"))
        self.AddButton(ID_BTN_RESET_CAM, c4d.BFH_SCALEFIT,
                       name=_t("reset_camera"))
        self.GroupEnd()

        self.AddSeparatorH(c4d.BFH_SCALEFIT)

        # About footer
        self.GroupBegin(GRP_ABOUT, c4d.BFH_SCALEFIT, cols=1)
        self.GroupBorderSpace(8, 6, 8, 6)
        self.AddStaticText(ID_ABOUT_NAME, c4d.BFH_CENTER,
                           name="HandNavigator for C4D")
        author_line = _t("author_by") + " " + PLUGIN_AUTHOR
        self.AddStaticText(ID_ABOUT_AUTHOR, c4d.BFH_CENTER,
                           name=author_line)
        self.AddStaticText(ID_ABOUT_SITE, c4d.BFH_CENTER,
                           name=PLUGIN_WEBSITE)
        self.AddStaticText(ID_ABOUT_LICENSE, c4d.BFH_CENTER,
                           name=_t("license"))
        self.GroupEnd()

        return True

    # ── Init ──────────────────────────────────────────────────────────────

    def InitValues(self):
        self.SetInt32(ID_ORBIT_SLIDER, int(self._orbit_sens),
                      min=ORBIT_MIN, max=ORBIT_MAX)
        self.SetInt32(ID_PAN_SLIDER, int(self._pan_sens),
                      min=PAN_MIN, max=PAN_MAX)
        self.SetInt32(ID_ZOOM_SLIDER, int(self._zoom_sens),
                      min=ZOOM_MIN, max=ZOOM_MAX)
        self.SetInt32(ID_PORT_INPUT, self._port,
                      min=PORT_MIN, max=PORT_MAX)
        self.SetInt32(ID_INTERVAL_INPUT, self._timer_ms,
                      min=POLL_MIN, max=POLL_MAX)

        self._start_server()
        return True

    # ── Commands ──────────────────────────────────────────────────────────

    def Command(self, cmd_id, msg):
        if cmd_id == ID_ORBIT_SLIDER:
            self._orbit_sens = float(self.GetInt32(ID_ORBIT_SLIDER))
        elif cmd_id == ID_PAN_SLIDER:
            self._pan_sens = float(self.GetInt32(ID_PAN_SLIDER))
        elif cmd_id == ID_ZOOM_SLIDER:
            self._zoom_sens = float(self.GetInt32(ID_ZOOM_SLIDER))
        elif cmd_id == ID_BTN_DEFAULTS:
            self._restore_defaults()
        elif cmd_id == ID_BTN_RESET_CAM:
            cam = _get_active_camera()
            if cam:
                _reset_camera(cam)
                c4d.EventAdd()
        return True

    def _restore_defaults(self):
        """Reset all sliders to default values."""
        self._orbit_sens = DEFAULT_ORBIT_SENS
        self._pan_sens = DEFAULT_PAN_SENS
        self._zoom_sens = DEFAULT_ZOOM_SENS
        self.SetInt32(ID_ORBIT_SLIDER, int(DEFAULT_ORBIT_SENS))
        self.SetInt32(ID_PAN_SLIDER, int(DEFAULT_PAN_SENS))
        self.SetInt32(ID_ZOOM_SLIDER, int(DEFAULT_ZOOM_SENS))

    # ── Timer (UDP polling) ───────────────────────────────────────────────

    def Timer(self, msg):
        if self._sock is None:
            return

        count = 0
        last_action = ""
        while True:
            try:
                data, _ = self._sock.recvfrom(4096)
                cmd = json.loads(data.decode("utf-8"))
                last_action = cmd.get("action", "?")
                self._dispatch_command(cmd)
                count += 1
            except BlockingIOError:
                break
            except Exception as e:
                print("[HandNav] " + str(e))
                break

        if count > 0:
            self._total += count
            info = (last_action.upper() + " x" + str(count)
                    + " | total: " + str(self._total))
            self.SetString(ID_STATUS, info)
            c4d.EventAdd()

    # ── Command Dispatch ──────────────────────────────────────────────────

    def _dispatch_command(self, cmd: dict) -> None:
        """Route a UDP command to the appropriate navigation function."""
        cam = _get_active_camera()
        if cam is None:
            return

        action = cmd.get("action", "")

        if action == "orbit":
            dx = cmd.get("dx", 0.0) * self._orbit_sens
            dy = cmd.get("dy", 0.0) * self._orbit_sens
            _apply_orbit(cam, dx, dy)

        elif action == "pan":
            dx = cmd.get("dx", 0.0) * self._pan_sens
            dy = cmd.get("dy", 0.0) * self._pan_sens
            _apply_pan(cam, dx, dy)

        elif action == "zoom":
            dz = cmd.get("dz", 0.0) * self._zoom_sens
            _apply_zoom(cam, dz)

        elif action == "reset":
            _reset_camera(cam)

    # ── UDP Server ────────────────────────────────────────────────────────

    def _start_server(self):
        """Create and bind the UDP socket."""
        self._stop_server()
        try:
            self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._sock.bind((DEFAULT_HOST, self._port))
            self._sock.setblocking(False)
            status = _t("listening", host=DEFAULT_HOST, port=self._port)
            self.SetString(ID_STATUS, status)
            print("[HandNav] " + status)
        except OSError as e:
            self.SetString(ID_STATUS, _t("error", msg=str(e)))
            print("[HandNav] Socket error: " + str(e))
            return
        self.SetTimer(self._timer_ms)

    def _stop_server(self):
        """Close the UDP socket if open."""
        if self._sock:
            self._sock.close()
            self._sock = None

    # ── Cleanup ───────────────────────────────────────────────────────────

    def DestroyWindow(self):
        self._stop_server()
        print("[HandNav] " + _t("server_stopped"))


# ─── Command Plugin (menu entry) ────────────────────────────────────────────

class HandNavCommand(c4d.plugins.CommandData):
    """Registers HandNavigator in the Extensions menu."""

    _dialog = None

    def Execute(self, doc):
        if self._dialog is None:
            self._dialog = HandNavDialog()
        return self._dialog.Open(
            dlgtype=c4d.DLG_TYPE_ASYNC,
            pluginid=PLUGIN_ID,
            defaultw=320,
            defaulth=280,
        )

    def RestoreLayout(self, sec_ref):
        if self._dialog is None:
            self._dialog = HandNavDialog()
        return self._dialog.RestoreLayout(pluginid=PLUGIN_ID, secret=sec_ref)


# ─── Registration ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    c4d.plugins.RegisterCommandPlugin(
        id=PLUGIN_ID,
        str=_t("plugin_name"),
        info=0,
        icon=None,
        help=_t("plugin_help"),
        dat=HandNavCommand(),
    )
    print("[HandNav] v" + PLUGIN_VERSION + " registered")
