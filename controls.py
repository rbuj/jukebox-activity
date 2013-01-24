# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307
# USA

# Copyright (C) 2013 Manuel Kaufmann <humitos@gmail.com>

import logging

from gi.repository import Gtk
from gi.repository import Gst
from gi.repository import GObject

from gettext import gettext as _

from sugar3 import mime
from sugar3.graphics.toolbutton import ToolButton
from sugar3.graphics.objectchooser import ObjectChooser


class Controls(GObject.GObject):
    """Class to create the Control (play, back, forward,
    add, remove, etc) toolbar"""

    SCALE_UPDATE_INTERVAL = 1000

    def __init__(self, activity, toolbar):
        GObject.GObject.__init__(self)

        self.activity = activity
        self.toolbar = toolbar

        self._scale_update_id = -1
        self._scale_changed_id = -1
        self._seek_timeout_id = -1

        self.open_button = ToolButton('list-add')
        self.open_button.set_tooltip(_('Add track'))
        self.open_button.show()
        self.open_button.connect('clicked', self.__open_button_clicked_cb)
        self.toolbar.insert(self.open_button, -1)

        erase_playlist_entry_btn = ToolButton(icon_name='list-remove')
        erase_playlist_entry_btn.set_tooltip(_('Remove track'))
        erase_playlist_entry_btn.connect('clicked',
                 self.__erase_playlist_entry_clicked_cb)
        self.toolbar.insert(erase_playlist_entry_btn, -1)

        spacer = Gtk.SeparatorToolItem()
        self.toolbar.insert(spacer, -1)
        spacer.show()

        self.prev_button = ToolButton('player_rew')
        self.prev_button.set_tooltip(_('Previous'))
        self.prev_button.show()
        self.prev_button.connect('clicked', self.__prev_button_clicked_cb)
        self.toolbar.insert(self.prev_button, -1)

        self.pause_image = Gtk.Image.new_from_stock(Gtk.STOCK_MEDIA_PAUSE,
                                                    Gtk.IconSize.BUTTON)
        self.pause_image.show()
        self.play_image = Gtk.Image.new_from_stock(Gtk.STOCK_MEDIA_PLAY,
                                                   Gtk.IconSize.BUTTON)
        self.play_image.show()

        self.button = Gtk.ToolButton()
        self.button.set_icon_widget(self.play_image)
        self.button.set_property('can-default', True)
        self.button.show()
        self.button.connect('clicked', self._button_clicked_cb)

        self.toolbar.insert(self.button, -1)

        self.next_button = ToolButton('player_fwd')
        self.next_button.set_tooltip(_('Next'))
        self.next_button.show()
        self.next_button.connect('clicked', self.__next_button_clicked_cb)
        self.toolbar.insert(self.next_button, -1)

        current_time = Gtk.ToolItem()
        self.current_time_label = Gtk.Label(label='')
        current_time.add(self.current_time_label)
        current_time.show()
        self.toolbar.insert(current_time, -1)

        self.adjustment = Gtk.Adjustment(0.0, 0.00, 100.0, 0.1, 1.0, 1.0)
        self.hscale = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL,
                                adjustment=self.adjustment)
        self.hscale.set_draw_value(False)
        # FIXME: this seems to be deprecated
        # self.hscale.set_update_policy(Gtk.UPDATE_CONTINUOUS)
        logging.debug("FIXME: AttributeError: 'Scale' object has no "
                      "attribute 'set_update_policy'")
        self.hscale.connect('button-press-event',
                self.__scale_button_press_cb)
        self.hscale.connect('button-release-event',
                self.__scale_button_release_cb)

        self.scale_item = Gtk.ToolItem()
        self.scale_item.set_expand(True)
        self.scale_item.add(self.hscale)
        self.toolbar.insert(self.scale_item, -1)

        total_time = Gtk.ToolItem()
        self.total_time_label = Gtk.Label(label='')
        total_time.add(self.total_time_label)
        total_time.show()
        self.toolbar.insert(total_time, -1)

        self.activity.connect('playlist-finished', self.__playlist_finished_cb)
        self.activity.player.connect('play', self.__player_play)

    def __player_play(self, widget):
        if self._scale_update_id == -1:
            self._scale_update_id = GObject.timeout_add(
                self.SCALE_UPDATE_INTERVAL, self.__update_scale_cb)
        self.set_enabled()
        self.set_button_pause()

    def __open_button_clicked_cb(self, widget):
        self.show_picker_cb()

    def __erase_playlist_entry_clicked_cb(self, widget):
        self.activity.playlist_widget.delete_selected_items()
        self.check_if_next_prev()

    def show_picker_cb(self, button=None):
        jobject = None
        chooser = ObjectChooser(self.activity,
                                what_filter=mime.GENERIC_TYPE_AUDIO)

        try:
            result = chooser.run()
            if result == Gtk.ResponseType.ACCEPT:
                jobject = chooser.get_selected_object()
                if jobject and jobject.file_path:
                    logging.info('Adding %s', jobject.file_path)
                    self.activity.playlist_widget.load_file(jobject)
                    self.check_if_next_prev()

                    if button is not None:
                        self.activity._switch_canvas(False)
                        self.activity._view_toolbar.\
                            _show_playlist.set_active(True)
        finally:
            if jobject is not None:
                jobject.destroy()

    def __prev_button_clicked_cb(self, widget):
        self.activity.songchange('prev')

    def __next_button_clicked_cb(self, widget):
        self.activity.songchange('next')

    def check_if_next_prev(self):
        current_playing = self.activity.playlist_widget._current_playing
        if len(self.activity.playlist_widget._items) == 0:
            # There is no media in the playlist
            self.prev_button.set_sensitive(False)
            self.button.set_sensitive(False)
            self.next_button.set_sensitive(False)
        else:
            self.button.set_sensitive(True)

            current_playing = self.activity.playlist_widget._current_playing
            if current_playing == 0:
                self.prev_button.set_sensitive(False)
            else:
                self.prev_button.set_sensitive(True)

            items = len(self.activity.playlist_widget._items)
            if current_playing == items - 1:
                self.next_button.set_sensitive(False)
            else:
                self.next_button.set_sensitive(True)

    def _button_clicked_cb(self, widget):
        self.set_enabled()

        if self.activity.player.is_playing():
            self.activity.player.pause()
            self.set_button_play()
            GObject.source_remove(self._scale_update_id)
        else:
            if self.activity.player.error:
                self.set_disabled()
            else:
                if self.activity.player.player.props.current_uri is None:
                    # There is no stream selected to be played
                    # yet. Select the first one
                    path = self.activity.playlist_widget._items[0]['path']
                    self.activity.playlist_widget._current_playing = 0
                    self.activity.player.set_uri(path)

                self.activity.player.play()
                self.activity._switch_canvas(True)
                self._scale_update_id = GObject.timeout_add(
                    self.SCALE_UPDATE_INTERVAL, self.__update_scale_cb)

    def set_button_play(self):
        self.button.set_icon_widget(self.play_image)

    def set_button_pause(self):
        self.button.set_icon_widget(self.pause_image)

    def set_disabled(self):
        self.button.set_sensitive(False)
        self.scale_item.set_sensitive(False)
        self.hscale.set_sensitive(False)

    def set_enabled(self):
        self.button.set_sensitive(True)
        self.scale_item.set_sensitive(True)
        self.hscale.set_sensitive(True)

    def __scale_button_press_cb(self, widget, event):
        self.button.set_sensitive(False)
        self.was_playing = self.activity.player.is_playing()
        if self.was_playing:
            self.activity.player.pause()

        # don't timeout-update position during seek
        if self._scale_update_id != -1:
            GObject.source_remove(self._scale_update_id)
            self._scale_update_id = -1

        # make sure we get changed notifies
        if self._scale_changed_id == -1:
            self._scale_changed_id = self.hscale.connect('value-changed',
                self.__scale_value_changed_cb)

    def __scale_value_changed_cb(self, scale):
        # see seek.c:seek_cb
        real = long(scale.get_value() * self.p_duration / 100)  # in ns
        self.activity.player.seek(real)
        # allow for a preroll
        self.activity.player.get_state(timeout=50 * Gst.MSECOND)  # 50 ms

    def __scale_button_release_cb(self, widget, event):
        # see seek.cstop_seek
        widget.disconnect(self._scale_changed_id)
        self._scale_changed_id = -1

        self.button.set_sensitive(True)
        if self._seek_timeout_id != -1:
            GObject.source_remove(self._seek_timeout_id)
            self._seek_timeout_id = -1
        else:
            if self.was_playing:
                self.activity.player.play()

        if self._scale_update_id != -1:
            # self.error('Had a previous update timeout id')
            pass
        else:
            self._scale_update_id = GObject.timeout_add(
                self.SCALE_UPDATE_INTERVAL, self.__update_scale_cb)

    def __update_scale_cb(self):
        success, self.p_position, self.p_duration = \
            self.activity.player.query_position()

        if not success:
            return True

        if self.p_position != Gst.CLOCK_TIME_NONE:
            value = self.p_position * 100.0 / self.p_duration
            self.adjustment.set_value(value)

            # Update the current time
            seconds = self.p_position * 10 ** -9
            time = '%2d:%02d' % (int(seconds / 60), int(seconds % 60))
            self.current_time_label.set_text(time)

        # FIXME: this should be updated just once when the file starts
        # the first time
        if self.p_duration != Gst.CLOCK_TIME_NONE:
            seconds = self.p_duration * 10 ** -9
            time = '%2d:%02d' % (int(seconds / 60), int(seconds % 60))
            self.total_time_label.set_text(time)

        return True

    def __playlist_finished_cb(self, widget):
        self.activity.player.stop()
        self.set_button_play()
        self.check_if_next_prev()

        self.adjustment.set_value(0)
        self.current_time_label.set_text('')
        self.total_time_label.set_text('')
