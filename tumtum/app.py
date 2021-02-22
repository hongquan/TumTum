# Copyright © 2020, Nguyễn Hồng Quân <ng.hong.quan@gmail.com>

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#       http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import os
from gettext import gettext as _
from typing import Optional, Dict
from queue import Queue, Empty
from dataclasses import dataclass

import gi
import logbook
import cairo
import numpy as np
import face_recognition
from logbook import Logger
from PIL import Image

gi.require_version('GLib', '2.0')
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
gi.require_version('Gio', '2.0')
gi.require_version('Gst', '1.0')
gi.require_version('GstBase', '1.0')
gi.require_version('GstApp', '1.0')
gi.require_foreign('cairo')

from gi.repository import GLib, Gtk, Gdk, Gio, Gst, GstBase, GstApp

from .consts import APP_ID, SHORT_NAME
from . import __version__
from . import ui
from .resources import get_ui_filepath
from .prep import get_device_path


logger = Logger(__name__)
Gst.init(None)
CONTROL_MASK = Gdk.ModifierType.CONTROL_MASK

# Some Gstreamer CLI examples
# gst-launch-1.0 v4l2src device=/dev/video0 ! videoconvert ! waylandsink
# gst-launch-1.0 playbin3 uri=v4l2:///dev/video0 video-sink=waylandsink
# Better integration:
#   gst-launch-1.0 v4l2src device=/dev/video0 ! videoconvert ! gtksink
#   gst-launch-1.0 v4l2src ! videoconvert ! glsinkbin sink=gtkglsink


@dataclass
class OverlayDrawData:
    face_box: Optional[cairo.Rectangle] = None
    nose_box: Optional[cairo.Rectangle] = None


class TumTumApplication(Gtk.Application):
    SINK_NAME = 'sink'
    APPSINK_NAME = 'app_sink'
    STACK_CHILD_NAME_WEBCAM = 'src_webcam'
    STACK_CHILD_NAME_IMAGE = 'src_image'
    GST_SOURCE_NAME = 'webcam_source'
    GST_OVERLAY_NAME = 'overlay_cairo'
    window: Optional[Gtk.Window] = None
    main_grid: Optional[Gtk.Grid] = None
    area_webcam: Optional[Gtk.Widget] = None
    cont_webcam: Optional[Gtk.Overlay] = None
    stack_img_source: Optional[Gtk.Stack] = None
    btn_play: Optional[Gtk.RadioToolButton] = None
    # We connect Play button with "toggled" signal, but when we want to imitate mouse click on the button,
    # calling "set_active" on it doesn't work! We have to call on the Pause button instead
    btn_pause: Optional[Gtk.RadioToolButton] = None
    btn_img_chooser: Optional[Gtk.FileChooserButton] = None
    gst_pipeline: Optional[Gst.Pipeline] = None
    raw_result_buffer: Optional[Gtk.TextBuffer] = None
    webcam_combobox: Optional[Gtk.ComboBox] = None
    webcam_store: Optional[Gtk.ListStore] = None
    frame_image: Optional[Gtk.AspectFrame] = None
    # Box holds the emplement to display when no image is chosen
    box_image_empty: Optional[Gtk.Box] = None
    devmonitor: Optional[Gst.DeviceMonitor] = None
    clipboard: Optional[Gtk.Clipboard] = None
    result_display: Optional[Gtk.Frame] = None
    progress_bar: Optional[Gtk.ProgressBar] = None
    infobar: Optional[Gtk.InfoBar] = None
    raw_result_expander: Optional[Gtk.Expander] = None
    g_event_sources: Dict[str, int] = {}
    overlay_queue: 'Queue[OverlayDrawData]' = Queue(1)

    def __init__(self, *args, **kwargs):
        super().__init__(
            *args, application_id=APP_ID, flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE, **kwargs
        )
        self.add_main_option(
            'verbose', ord('v'), GLib.OptionFlags.NONE, GLib.OptionArg.NONE,
            "More detailed log", None
        )

    def do_startup(self):
        Gtk.Application.do_startup(self)
        self.setup_actions()
        devmonitor = Gst.DeviceMonitor.new()
        devmonitor.add_filter('Video/Source', Gst.Caps.from_string('video/x-raw'))
        logger.debug('Monitor: {}', devmonitor)
        self.devmonitor = devmonitor

    def setup_actions(self):
        action_quit = Gio.SimpleAction.new(_('quit'), None)
        action_quit.connect('activate', self.quit_from_action)
        self.add_action(action_quit)
        action_about = Gio.SimpleAction.new(_('about'), None)
        action_about.connect('activate', self.show_about_dialog)
        self.add_action(action_about)

    def build_gstreamer_pipeline(self):
        # https://gstreamer.freedesktop.org/documentation/application-development/advanced/pipeline-manipulation.html?gi-language=c#grabbing-data-with-appsink
        # Try GL backend first
        command = (f'v4l2src name={self.GST_SOURCE_NAME} ! tee name=t ! '
                   f'queue ! videoconvert ! cairooverlay name={self.GST_OVERLAY_NAME} ! '
                   f'glsinkbin sink="gtkglsink name={self.SINK_NAME}" name=sink_bin '
                   't. ! queue leaky=2 max-size-buffers=2 ! videoconvert ! video/x-raw,format=RGB !'
                   f'appsink name={self.APPSINK_NAME} max_buffers=2 drop=1')
        logger.debug('To build pipeline: {}', command)
        try:
            pipeline = Gst.parse_launch(command)
        except GLib.Error as e:
            logger.debug('Error: {}', e)
            pipeline = None
        if not pipeline:
            logger.info('OpenGL is not available, fallback to normal GtkSink')
            # Fallback to non-GL
            command = (f'v4l2src name={self.GST_SOURCE_NAME} ! videoconvert ! tee name=t ! '
                       f'queue ! cairooverlay name={self.GST_OVERLAY_NAME} ! gtksink name={self.SINK_NAME} '
                       't. ! queue leaky=1 max-size-buffers=2 ! video/x-raw,format=RGB ! '
                       f'appsink name={self.APPSINK_NAME}')
            logger.debug('To build pipeline: {}', command)
            try:
                pipeline = Gst.parse_launch(command)
            except GLib.Error as e:
                # TODO: Print error in status bar
                logger.error('Failed to create Gst Pipeline. Error: {}', e)
                return
        logger.debug('Created {}', pipeline)
        appsink: GstApp.AppSink = pipeline.get_by_name(self.APPSINK_NAME)
        logger.debug('Appsink: {}', appsink)
        appsink.connect('new-sample', self.on_new_webcam_sample)
        # Ref: https://gist.github.com/pmgration/273383a6e02e961b0af06e05fbf4349f
        gst_overlay = pipeline.get_by_name(self.GST_OVERLAY_NAME)
        logger.debug('Overlay: {}', gst_overlay)
        gst_overlay.connect('draw', self.on_overlay_draw, self.overlay_queue)
        self.gst_pipeline = pipeline
        return pipeline

    def build_main_window(self):
        source = get_ui_filepath('main.glade')
        builder: Gtk.Builder = Gtk.Builder.new_from_file(str(source))
        handlers = self.signal_handlers_for_glade()
        window: Gtk.Window = builder.get_object('main-window')
        builder.get_object('main-grid')
        window.set_application(self)
        self.set_accels_for_action('app.quit', ("<Ctrl>Q",))
        self.stack_img_source = builder.get_object('stack-img-source')
        self.btn_play = builder.get_object('btn-play')
        self.btn_pause = builder.get_object('btn-pause')
        self.btn_img_chooser = builder.get_object('btn-img-chooser')
        self.cont_webcam = builder.get_object('cont-webcam')
        if self.gst_pipeline:
            self.replace_webcam_placeholder_with_gstreamer_sink()
        self.raw_result_buffer = builder.get_object('raw-result-buffer')
        self.raw_result_expander = builder.get_object('raw-result-expander')
        self.webcam_store = builder.get_object('webcam-list')
        self.webcam_combobox = builder.get_object('webcam-combobox')
        self.frame_image = builder.get_object('frame-image')
        self.box_image_empty = builder.get_object('box-image-empty')
        main_menubutton: Gtk.MenuButton = builder.get_object('main-menubutton')
        main_menubutton.set_menu_model(ui.build_app_menu_model())
        self.frame_image.drag_dest_set(Gtk.DestDefaults.ALL, [], Gdk.DragAction.COPY)
        self.frame_image.drag_dest_add_uri_targets()
        self.clipboard = Gtk.Clipboard.get_for_display(Gdk.Display.get_default(),
                                                       Gdk.SELECTION_CLIPBOARD)
        self.result_display = builder.get_object('result-display-frame')
        self.progress_bar = builder.get_object('progress-bar')
        self.infobar = builder.get_object('info-bar')
        box_playpause = builder.get_object('evbox-playpause')
        self.cont_webcam.add_overlay(box_playpause)
        logger.debug('Connect signal handlers')
        builder.connect_signals(handlers)
        return window

    def signal_handlers_for_glade(self):
        return {
            'on_btn_play_toggled': self.play_webcam_video,
            'on_webcam_combobox_changed': self.on_webcam_combobox_changed,
            'on_evbox_playpause_enter_notify_event': self.on_evbox_playpause_enter_notify_event,
            'on_evbox_playpause_leave_notify_event': self.on_evbox_playpause_leave_notify_event,
            'on_info_bar_response': self.on_info_bar_response,
        }

    def discover_webcam(self):
        bus: Gst.Bus = self.devmonitor.get_bus()
        logger.debug('Bus: {}', bus)
        bus.add_watch(GLib.PRIORITY_DEFAULT, self.on_device_monitor_message, None)
        devices = self.devmonitor.get_devices()
        for d in devices:  # type: Gst.Device
            # Device is of private type GstV4l2Device or GstPipeWireDevice
            logger.debug('Found device {}', d.get_path_string())
            cam_name = d.get_display_name()
            cam_path = get_device_path(d)
            self.webcam_store.append((cam_path, cam_name))
        logger.debug('Start device monitoring')
        self.devmonitor.start()

    def do_activate(self):
        if not self.window:
            self.build_gstreamer_pipeline()
            self.window = self.build_main_window()
            self.discover_webcam()
        self.window.present()
        logger.debug("Window {} is shown", self.window)
        # If no webcam is selected, select the first one
        if not self.webcam_combobox.get_active_iter():
            self.webcam_combobox.set_active(0)

    def do_command_line(self, command_line: Gio.ApplicationCommandLine):
        options = command_line.get_options_dict().end().unpack()
        if options.get('verbose'):
            logger.level = logbook.DEBUG
            displayed_apps = os.getenv('G_MESSAGES_DEBUG', '').split()
            displayed_apps.append(SHORT_NAME)
            GLib.setenv('G_MESSAGES_DEBUG', ' '.join(displayed_apps), True)
        self.activate()
        return 0

    def replace_webcam_placeholder_with_gstreamer_sink(self):
        '''
        In glade file, we put a placeholder to reserve a place for putting webcam screen.
        Now it is time to replace that widget with which coming with gtksink.
        '''
        sink = self.gst_pipeline.get_by_name(self.SINK_NAME)
        area = sink.get_property('widget')
        old_area = self.cont_webcam.get_child()
        logger.debug('To replace {} with {}', old_area, area)
        self.cont_webcam.remove(old_area)
        self.cont_webcam.add(area)
        area.show()

    def reset_result(self):
        self.raw_result_buffer.set_text('')
        self.raw_result_expander.set_expanded(False)
        child = self.result_display.get_child()
        if child:
            self.result_display.remove(child)

    def on_device_monitor_message(self, bus: Gst.Bus, message: Gst.Message, user_data):
        logger.debug('Message: {}', message)
        # A private GstV4l2Device or GstPipeWireDevice type
        if message.type == Gst.MessageType.DEVICE_ADDED:
            added_dev: Optional[Gst.Device] = message.parse_device_added()
            if not added_dev:
                return True
            logger.debug('Added: {}', added_dev)
            cam_path = get_device_path(added_dev)
            cam_name = added_dev.get_display_name()
            # Check if this cam already in the list, add to list if not.
            for row in self.webcam_store:
                if row[0] == cam_path:
                    break
            else:
                self.webcam_store.append((cam_path, cam_name))
            return True
        elif message.type == Gst.MessageType.DEVICE_REMOVED:
            removed_dev: Optional[Gst.Device] = message.parse_device_removed()
            if not removed_dev:
                return True
            logger.debug('Removed: {}', removed_dev)
            cam_path = get_device_path(removed_dev)
            ppl_source = self.gst_pipeline.get_by_name(self.GST_SOURCE_NAME)
            if cam_path == ppl_source.get_property('device'):
                self.gst_pipeline.set_state(Gst.State.NULL)
            # Find the entry of just-removed in the list and remove it.
            itr: Optional[Gtk.TreeIter] = None
            for row in self.webcam_store:
                logger.debug('Row: {}', row)
                if row[0] == cam_path:
                    itr = row.iter
                    break
            if itr:
                logger.debug('To remove {} from list', cam_path)
                self.webcam_store.remove(itr)
        return True

    def on_webcam_combobox_changed(self, combo: Gtk.ComboBox):
        if not self.gst_pipeline:
            return
        liter = combo.get_active_iter()
        if not liter:
            return
        model = combo.get_model()
        path, name = model[liter]
        logger.debug('Picked {} {}', path, name)
        ppl_source = self.gst_pipeline.get_by_name(self.GST_SOURCE_NAME)
        self.gst_pipeline.set_state(Gst.State.NULL)
        ppl_source.set_property('device', path)
        self.gst_pipeline.set_state(Gst.State.PLAYING)
        app_sink = self.gst_pipeline.get_by_name(self.APPSINK_NAME)
        app_sink.set_emit_signals(True)

    def on_overlay_draw(self, _overlay: GstBase.BaseTransform, context: cairo.Context,
                        _timestamp: int, _duration: int, user_data: 'Queue[OverlayDrawData]'):
        try:
            draw_data = user_data.get_nowait()
        except Empty:
            return
        logger.debug('To draw {}', draw_data)
        context.rectangle(*draw_data.face_box)
        context.set_source_rgba(0.9, 0, 0, 0.6)
        context.set_line_width(4)
        context.stroke()

    def on_new_webcam_sample(self, appsink: GstApp.AppSink) -> Gst.FlowReturn:
        if appsink.is_eos():
            return Gst.FlowReturn.OK
        sample: Gst.Sample = appsink.try_pull_sample(0.5)
        buffer: Gst.Buffer = sample.get_buffer()
        caps: Gst.Caps = sample.get_caps()
        # This Pythonic usage is thank to python3-gst
        struct: Gst.Structure = caps[0]
        width = struct['width']
        height = struct['height']
        success: bool
        mapinfo: Gst.MapInfo
        success, mapinfo = buffer.map(Gst.MapFlags.READ)
        if not success:
            logger.error('Failed to get mapinfo.')
            return Gst.FlowReturn.ERROR
        # In Gstreamer 1.18, Gst.MapInfo.data is memoryview instead of bytes
        imgdata = mapinfo.data.tobytes() if isinstance(mapinfo.data, memoryview) else mapinfo.data
        img = Image.frombytes('RGB', (width, height), imgdata)
        nimp = np.asarray(img)
        results = face_recognition.face_locations(nimp)
        logger.debug('Result: {}', results)
        if results:
            # face_recognition return result as (top, right, bottom, left)
            t, r, b, le = results[0]
            rect = cairo.Rectangle(le, t, r - le, b - t)
            draw_data = OverlayDrawData(face_box=rect)
            self.overlay_queue.put_nowait(draw_data)
        return Gst.FlowReturn.OK

    def on_evbox_playpause_enter_notify_event(self, box: Gtk.EventBox, event: Gdk.EventCrossing):
        child: Gtk.Widget = box.get_child()
        child.set_opacity(1)

    def on_evbox_playpause_leave_notify_event(self, box: Gtk.EventBox, event: Gdk.EventCrossing):
        child: Gtk.Widget = box.get_child()
        child.set_opacity(0.2)

    def on_info_bar_response(self, infobar: Gtk.InfoBar, response_id: int):
        infobar.set_visible(False)

    def play_webcam_video(self, widget: Optional[Gtk.Widget] = None):
        if not self.gst_pipeline:
            return
        to_pause = (isinstance(widget, Gtk.RadioToolButton) and not widget.get_active())
        app_sink = self.gst_pipeline.get_by_name(self.APPSINK_NAME)
        source = self.gst_pipeline.get_by_name(self.GST_SOURCE_NAME)
        if to_pause:
            # Tell appsink to stop emitting signals
            logger.debug('Stop appsink from emitting signals')
            app_sink.set_emit_signals(False)
            r = source.set_state(Gst.State.READY)
            r = source.set_state(Gst.State.PAUSED)
            logger.debug('Change {} state to paused: {}', source.get_name(), r)
        else:
            r = source.set_state(Gst.State.PLAYING)
            logger.debug('Change {} state to playing: {}', source.get_name(), r)
            self.reset_result()
            # Delay set_emit_signals call to prevent scanning old frame
            GLib.timeout_add_seconds(1, app_sink.set_emit_signals, True)

    def show_about_dialog(self, action: Gio.SimpleAction, param: Optional[GLib.Variant] = None):
        if self.gst_pipeline:
            self.btn_pause.set_active(True)
        source = get_ui_filepath('about.glade')
        builder: Gtk.Builder = Gtk.Builder.new_from_file(str(source))
        dlg_about: Gtk.AboutDialog = builder.get_object('dlg-about')
        dlg_about.set_version(__version__)
        logger.debug('To present {}', dlg_about)
        dlg_about.present()

    def show_error(self, message: str):
        box: Gtk.Box = self.infobar.get_content_area()
        label: Gtk.Label = box.get_children()[0]
        label.set_label(message)
        self.infobar.set_message_type(Gtk.MessageType.ERROR)
        self.infobar.set_visible(True)

    def quit_from_action(self, action: Gio.SimpleAction, param: Optional[GLib.Variant] = None):
        self.quit()

    def quit(self):
        if self.gst_pipeline:
            self.gst_pipeline.set_state(Gst.State.NULL)
        super().quit()
