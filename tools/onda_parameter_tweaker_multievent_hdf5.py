#!/usr/bin/env python
#    This file is part of OnDA.
#
#    OnDA is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    OnDA is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with OnDA.  If not, see <http://www.gnu.org/licenses/>.


import argparse
import h5py
import numpy
import random
import signal
import sys

from configparser import ConfigParser

try:
    from PyQt5 import QtCore, QtGui
except ImportError:
    from PyQt4 import QtCore, QtGui
import pyqtgraph as pg

try:
    from GUI.UI.onda_crystallography_parameter_tweaker_ui_qt5 import Ui_MainWindow
except ImportError:
    from GUI.UI.onda_crystallography_parameter_tweaker_ui_qt4 import Ui_MainWindow
import cfelpyutils.cfel_optarg as coa
import cfelpyutils.cfel_hdf5 as ch5
import cfelpyutils.cfel_geom as cgm
import python_extensions.peakfinder8_extension as pf8


def _load_file(filename, hdf5_path, index):
    hdf5_fh = h5py.File(filename, 'r')
    data = hdf5_fh[hdf5_path][index, :, :]
    hdf5_fh.close()
    return data, filename


def _check_changed_parameter(param, param_conv_vers, lineedit_element):
    try:
        new_param = param_conv_vers(lineedit_element.text())
        if new_param != param:
            return new_param, True
        else:
            return param, False
    except ValueError:
        lineedit_element.setText(str(param))
        return param, False


class MainFrame(QtGui.QMainWindow):
    """
    The main frame of the application
    """

    def _draw_things(self):
        img, title = _load_file(self._filename, self._data_path, self._file_index)
        img = img.astype(numpy.float64)

        if self._apply_darkcal is True:
            img -= self._darkcal

        self._img_to_draw[self._pixel_maps[0], self._pixel_maps[1]] = img.ravel()
        self._ui.imageView.setImage(self._img_to_draw.T, autoLevels=False, autoRange=False, autoHistogramRange=False)
        self._mask_image_view.setImage(numpy.transpose(self._mask_to_draw, axes=(1, 0, 2)), autoLevels=False,
                                       autoRange=False, opacity=0.1)

        peak_list = pf8.peakfinder_8(
            self._max_num_peaks,
            img.astype(numpy.float32),
            self._mask.astype(numpy.int8),
            self._pixelmap_radius,
            self._asic_nx,
            self._asic_ny,
            self._nasics_x,
            self._nasics_y,
            self._adc_thresh,
            self._minimum_snr,
            self._min_pixel_count,
            self._max_pixel_count,
            self._local_bg_radius)

        if self._ui.showHidePeaksCheckBox.isChecked():

            peak_x = []
            peak_y = []
            for peak_fs, peak_ss in zip(peak_list[0], peak_list[1]):
                peak_in_slab = int(round(peak_ss)) * self.slab_shape[1] + int(round(peak_fs))
                try:
                    peak_x.append(self._pixel_maps[0][peak_in_slab])
                    peak_y.append(self._pixel_maps[1][peak_in_slab])
                except IndexError:
                    pass
            self._peak_canvas.setData(peak_y, peak_x, symbol='o', size=15, pen=self._ring_pen, brush=(0, 0, 0, 0),
                                      pxMode=False)

            hit = self._min_num_peaks_for_hit < len(peak_list[2]) < self._max_num_peaks_for_hit

            if hit:
                self._ui.hitLabel.setText('Hit [{0}-{1} peaks]: <b>Yes</b> ({2} peaks)'.format(
                    self._min_num_peaks_for_hit, self._max_num_peaks_for_hit, len(peak_list[2])))
            else:
                self._ui.hitLabel.setText('Hit [{0}-{1} peaks]: No ({2} peaks)'.format(
                    self._min_num_peaks_for_hit, self._max_num_peaks_for_hit, len(peak_list[2])))

        else:

            self._ui.hitLabel.setText('Hit [{0}-{1} peaks]: - (- peaks)'.format(self._min_num_peaks_for_hit,
                                                                                self._max_num_peaks_for_hit))
            self._peak_canvas.setData([])

        if self._ui.resolutionRingsCheckBox.isChecked():
            self._circle_canvas.setData([self.img_shape[1] / 2, self.img_shape[1] / 2],
                                        [self.img_shape[0] / 2, self.img_shape[0] / 2],
                                        symbol='o', size=[2 * self._min_res, 2 * self._max_res],
                                        pen=self._circle_pen, brush=(0, 0, 0, 0), pxMode=False)

        else:

            self._circle_canvas.setData([])

        self.setWindowTitle('%g - %s' % (self._file_index, title))

    def _update_peaks(self):

        something_changed = False
        self._adc_thresh, changed = _check_changed_parameter(self._adc_thresh, float, self._adc_threshold_lineedit)
        if changed:
            something_changed = True
        self._minimum_snr, changed = _check_changed_parameter(self._minimum_snr, float, self._min_snr_lineedit)
        if changed:
            something_changed = True
        self._min_pixel_count, changed = _check_changed_parameter(self._min_pixel_count, int,
                                                                  self._min_pixel_count_lineedit)
        if changed:
            something_changed = True
        self._max_pixel_count, changed = _check_changed_parameter(self._max_pixel_count, int,
                                                                  self._max_pixel_count_lineedit)
        if changed:
            something_changed = True
        self._local_bg_radius, changed = _check_changed_parameter(self._local_bg_radius, int,
                                                                  self._local_bg_radius_lineedit)
        if changed:
            something_changed = True
        self._min_res, changed = _check_changed_parameter(self._min_res, int, self._min_res_lineedit)
        if changed:
            something_changed = True
        self._max_res, changed = _check_changed_parameter(self._max_res, int, self._max_res_lineedit)
        if changed:
            something_changed = True

        self._res_mask = numpy.ones(self.slab_shape, dtype=numpy.int8)
        self._res_mask[numpy.where(self._pixelmap_radius < self._min_res)] = 0
        self._res_mask[numpy.where(self._pixelmap_radius > self._max_res)] = 0
        self._mask = self._loaded_mask * self._res_mask

        if something_changed:
            self._draw_things()

    def _previous_event(self):

        if self._file_index == 0:
            self._file_index = self._num_events - 1
        else:
            self._file_index -= 1
        self._draw_things()

    def _next_event(self):

        if self._file_index == self._num_events - 1:
            self._file_index = 0
        else:
            self._file_index += 1
        self._draw_things()

    def _random_event(self):
        self._file_index = random.randrange(0, self._num_events)
        self._draw_things()

    def _mouse_clicked(self, event):
        pos = event[0].scenePos()
        if self._ui.imageView.getView().sceneBoundingRect().contains(pos):
            mouse_point = self._ui.imageView.getView().mapSceneToView(pos)
            x_mouse = int(mouse_point.x())
            y_mouse = int(mouse_point.y())
            if 0 < x_mouse < self._img_to_draw.shape[1] and 0 < y_mouse < self._img_to_draw.shape[0]:
                self._ui.lastClickedPositionLabel.setText('Last clicked position: (%g,%g)' % (x_mouse, y_mouse))
                self._ui.lastClickedPixelValueLabel.setText('Pixel Value: %5.1f' % (self._img_to_draw[y_mouse,
                                                                                                      x_mouse]))

    def __init__(self, input_file, data_path, apply_darkcal, monitor_params, ):

        QtCore.QObject.__init__(self)

        self._filename = input_file
        self._data_path = data_path
        self._apply_darkcal = apply_darkcal

        with h5py.File(self._filename, 'r') as fh:
            self._num_events = fh[self._data_path].shape[0]

        self._file_index = 0

        self.monitor_params = monitor_params

        gen_params = monitor_params['General']
        p8pd_params = monitor_params['Peakfinder8PeakDetection']
        dkc_params = monitor_params['DarkCalCorrection']

        self._ring_pen = pg.mkPen('r', width=2)
        self._circle_pen = pg.mkPen('b', width=2)

        pix_maps = cgm.pixel_maps_from_geometry_file(gen_params['geometry_file'])
        self._pixelmap_radius = pix_maps[2]

        if apply_darkcal is True:
            self._darkcal = ch5.load_nparray_from_hdf5_file(dkc_params['filename'], dkc_params['hdf5_group'])

        self._pixel_maps, self.slab_shape, self.img_shape = cgm.pixel_maps_for_image_view(gen_params['geometry_file'])
        self._img_to_draw = numpy.zeros(self.img_shape, dtype=numpy.float32)
        self._mask_to_draw = numpy.zeros(self.img_shape + (3,), dtype=numpy.int16)
        self._max_num_peaks = int(p8pd_params['max_num_peaks'])
        self._asic_nx = int(p8pd_params['asics_nx'])
        self._asic_ny = int(p8pd_params['asics_ny'])
        self._nasics_x = int(p8pd_params['nasics_x'])
        self._nasics_y = int(p8pd_params['nasics_y'])
        self._adc_thresh = float(p8pd_params['adc_threshold'])
        self._minimum_snr = float(p8pd_params['minimum_snr'])
        self._min_pixel_count = int(p8pd_params['min_pixel_count'])
        self._max_pixel_count = int(p8pd_params['max_pixel_count'])
        self._local_bg_radius = int(p8pd_params['local_bg_radius'])
        self._mask_filename = p8pd_params['mask_filename']
        self._mask_hdf5_path = p8pd_params['mask_hdf5_path']
        self._min_res = int(p8pd_params['min_res'])
        self._max_res = int(p8pd_params['max_res'])
        self._loaded_mask = ch5.load_nparray_from_hdf5_file(self._mask_filename, self._mask_hdf5_path)
        self._min_num_peaks_for_hit = int(monitor_params['General']['min_num_peaks_for_hit'])
        self._max_num_peaks_for_hit = int(monitor_params['General']['max_num_peaks_for_hit'])

        self._res_maskmask = numpy.ones(self.slab_shape, dtype=numpy.int8)
        self._res_mask[numpy.where(self._pixelmap_radius < self._min_res)] = 0
        self._res_mask[numpy.where(self._pixelmap_radius > self._max_res)] = 0
        self._mask = self._loaded_mask * self._res_mask

        mask = self._loaded_mask.copy().astype(numpy.float)
        mask = mask * 255. / mask.max()
        mask = 255. - mask
        self._mask_to_draw[self._pixel_maps[0], self._pixel_maps[1], 1] = mask.ravel()

        self._mask_image_view = pg.ImageItem()
        self._peak_canvas = pg.ScatterPlotItem()
        self._circle_canvas = pg.ScatterPlotItem()

        self._adc_threshold_label = QtGui.QLabel(self)
        self._adc_threshold_label.setText('adc_threshold')
        self._adc_threshold_lineedit = QtGui.QLineEdit(self)
        self._adc_threshold_lineedit.setText(str(p8pd_params['adc_threshold']))
        self._adc_threshold_lineedit.editingFinished.connect(self._update_peaks)
        self._hlayout0 = QtGui.QHBoxLayout()
        self._hlayout0.addWidget(self._adc_threshold_label)
        self._hlayout0.addWidget(self._adc_threshold_lineedit)

        self._min_snr_label = QtGui.QLabel(self)
        self._min_snr_label.setText('minmum_snr')
        self._min_snr_lineedit = QtGui.QLineEdit(self)
        self._min_snr_lineedit.setText(str(p8pd_params['minimum_snr']))
        self._min_snr_lineedit.editingFinished.connect(self._update_peaks)
        self._hlayout1 = QtGui.QHBoxLayout()
        self._hlayout1.addWidget(self._min_snr_label)
        self._hlayout1.addWidget(self._min_snr_lineedit)

        self._min_pixel_count_label = QtGui.QLabel(self)
        self._min_pixel_count_label.setText('min_pixel_count')
        self._min_pixel_count_lineedit = QtGui.QLineEdit(self)
        self._min_pixel_count_lineedit.setText(str(p8pd_params['min_pixel_count']))
        self._min_pixel_count_lineedit.editingFinished.connect(self._update_peaks)
        self._hlayout2 = QtGui.QHBoxLayout()
        self._hlayout2.addWidget(self._min_pixel_count_label)
        self._hlayout2.addWidget(self._min_pixel_count_lineedit)

        self._max_pixel_count_label = QtGui.QLabel(self)
        self._max_pixel_count_label.setText('max_pixel_count')
        self._max_pixel_count_lineedit = QtGui.QLineEdit(self)
        self._max_pixel_count_lineedit.setText(str(p8pd_params['max_pixel_count']))
        self._max_pixel_count_lineedit.editingFinished.connect(self._update_peaks)
        self._hlayout3 = QtGui.QHBoxLayout()
        self._hlayout3.addWidget(self._max_pixel_count_label)
        self._hlayout3.addWidget(self._max_pixel_count_lineedit)

        self._local_bg_radius_label = QtGui.QLabel(self)
        self._local_bg_radius_label.setText('local_bg_raidus')
        self._local_bg_radius_lineedit = QtGui.QLineEdit(self)
        self._local_bg_radius_lineedit.setText(str(p8pd_params['local_bg_radius']))
        self._local_bg_radius_lineedit.editingFinished.connect(self._update_peaks)
        self._hlayout4 = QtGui.QHBoxLayout()
        self._hlayout4.addWidget(self._local_bg_radius_label)
        self._hlayout4.addWidget(self._local_bg_radius_lineedit)

        self._min_res_label = QtGui.QLabel(self)
        self._min_res_label.setText('min_res')
        self._min_res_lineedit = QtGui.QLineEdit(self)
        self._min_res_lineedit.setText(str(self._min_res))
        self._min_res_lineedit.editingFinished.connect(self._update_peaks)
        self._hlayout5 = QtGui.QHBoxLayout()
        self._hlayout5.addWidget(self._min_res_label)
        self._hlayout5.addWidget(self._min_res_lineedit)

        self._max_res_label = QtGui.QLabel(self)
        self._max_res_label.setText('max_res')
        self._max_res_lineedit = QtGui.QLineEdit(self)
        self._max_res_lineedit.setText(str(self._max_res))
        self._max_res_lineedit.editingFinished.connect(self._update_peaks)
        self._hlayout6 = QtGui.QHBoxLayout()
        self._hlayout6.addWidget(self._max_res_label)
        self._hlayout6.addWidget(self._max_res_lineedit)

        self._param_label = QtGui.QLabel(self)
        self._param_label.setText('<b>Peakfinder Parameters:</b>')

        self._ui = Ui_MainWindow()
        self._ui.setupUi(self)
        self.init_ui()

        self._proxy = pg.SignalProxy(self._ui.imageView.getView().scene().sigMouseClicked,
                                     slot=self._mouse_clicked)

        self._update_peaks()
        self._draw_things()
        self.show()

    def init_ui(self):

        self._ui.imageView.ui.menuBtn.hide()
        self._ui.imageView.ui.roiBtn.hide()

        self._ui.imageView.getView().addItem(self._mask_image_view)
        self._ui.imageView.getView().addItem(self._peak_canvas)
        self._ui.imageView.getView().addItem(self._circle_canvas)
        self._ui.forwardButton.clicked.connect(self._next_event)
        self._ui.backButton.clicked.connect(self._previous_event)
        self._ui.randomButton.clicked.connect(self._random_event)

        self._ui.verticalLayout1.insertLayout(0, self._hlayout6)
        self._ui.verticalLayout1.insertLayout(0, self._hlayout5)
        self._ui.verticalLayout1.insertLayout(0, self._hlayout4)
        self._ui.verticalLayout1.insertLayout(0, self._hlayout3)
        self._ui.verticalLayout1.insertLayout(0, self._hlayout2)
        self._ui.verticalLayout1.insertLayout(0, self._hlayout1)
        self._ui.verticalLayout1.insertLayout(0, self._hlayout0)
        self._ui.verticalLayout1.insertWidget(0, self._param_label)
        self._ui.splitter.setStretchFactor(0, 1)
        self._ui.splitter.setStretchFactor(1, 0)

        self._ui.showHidePeaksCheckBox.stateChanged.connect(self._draw_things)
        self._ui.resolutionRingsCheckBox.stateChanged.connect(self._draw_things)


def main():
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    config = ConfigParser()

    parser = argparse.ArgumentParser(prog='onda_parameter_tweaker_multievent_hdf5.py',
                                     description='OnDA parameter tweaker for multievent hdf5 files')
    parser.add_argument('hdf5_file_name', type=str, help='multievent hdf5 file name')
    parser.add_argument('hdf5_data_path', type=str, help='internal path to data (in the hdf5 file structure)')
    parser.add_argument('-d', '--darkcal', action='store_true', default=False,
                        help='subtract darkcal (file name taken from monitor.ini file)')
    args = parser.parse_args()

    input_file = args.hdf5_file_name
    data_path = args.hdf5_data_path
    apply_darkcal = args.darkcal

    config.read('monitor.ini')
    monitor_params = coa.parse_parameters(config)

    app = QtGui.QApplication(sys.argv)
    _ = MainFrame(input_file, data_path, apply_darkcal, monitor_params)
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
