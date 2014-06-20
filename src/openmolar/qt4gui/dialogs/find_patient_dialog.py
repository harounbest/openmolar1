#! /usr/bin/env python
# -*- coding: utf-8 -*-

# ############################################################################ #
# #                                                                          # #
# # Copyright (c) 2009-2014 Neil Wallace <neil@openmolar.com>                # #
# #                                                                          # #
# # This file is part of OpenMolar.                                          # #
# #                                                                          # #
# # OpenMolar is free software: you can redistribute it and/or modify        # #
# # it under the terms of the GNU General Public License as published by     # #
# # the Free Software Foundation, either version 3 of the License, or        # #
# # (at your option) any later version.                                      # #
# #                                                                          # #
# # OpenMolar is distributed in the hope that it will be useful,             # #
# # but WITHOUT ANY WARRANTY; without even the implied warranty of           # #
# # MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the            # #
# # GNU General Public License for more details.                             # #
# #                                                                          # #
# # You should have received a copy of the GNU General Public License        # #
# # along with OpenMolar.  If not, see <http://www.gnu.org/licenses/>.       # #
# #                                                                          # #
# ############################################################################ #

from __future__ import division

import datetime
import logging
from PyQt4 import QtGui, QtCore

from openmolar.settings import localsettings

from openmolar.dbtools import search

from openmolar.qt4gui.compiled_uis import Ui_patient_finder
from openmolar.qt4gui.dialogs.base_dialogs import ExtendableDialog


class FindPatientDialog(QtGui.QDialog, Ui_patient_finder.Ui_Dialog):

    chosen_sno = None

    def __init__(self, parent=None):
        QtGui.QDialog.__init__(self, parent)
        self.setupUi(self)

        self.sname.setFocus()

        self.repeat_pushButton.clicked.connect(self.repeat_last_search)

    def repeat_last_search(self):
        self.dateEdit.setDate(localsettings.lastsearch[2])
        self.addr1.setText(localsettings.lastsearch[4])
        self.tel.setText(localsettings.lastsearch[3])
        self.sname.setText(localsettings.lastsearch[0])
        self.fname.setText(localsettings.lastsearch[1])
        self.pcde.setText(localsettings.lastsearch[5])

    def exec_(self):
        if localsettings.PT_COUNT == 0:
            QtGui.QMessageBox.warning(self.parent(), _("warning"),
                                      _("You have no patients in your database"))
            return False
        if localsettings.PT_COUNT < 5 or QtGui.QDialog.exec_(self):
            dob = self.dateEdit.date().toPyDate()
            addr = str(self.addr1.text().toAscii())
            tel = str(self.tel.text().toAscii())
            sname = str(self.sname.text().toAscii())
            fname = str(self.fname.text().toAscii())
            pcde = str(self.pcde.text().toAscii())
            localsettings.lastsearch = (sname, fname, dob, tel, addr, pcde)

            try:
                serialno = int(sname)
            except:
                serialno = 0

            if serialno > 0:
                self.chosen_sno = serialno
            else:
                candidates = search.getcandidates(
                    dob, addr, tel, sname,
                    self.snameSoundex_checkBox.checkState(), fname,
                    self.fnameSoundex_checkBox.checkState(), pcde
                )

                if candidates == () and localsettings.PT_COUNT > 5:
                    QtGui.QMessageBox.warning(self.parent(), "warning",
                                              _("no match found"))
                    return False
                else:
                    if localsettings.PT_COUNT < 5:
                            candidates = search.all_patients()
                    if len(candidates) == 1:
                        self.chosen_sno = int(candidates[0][0])
                    else:
                        dl = FinalChoiceDialog(candidates, self)
                        if dl.exec_():
                            self.chosen_sno = dl.chosen_sno
            return True

        return False


class FinalChoiceDialog(ExtendableDialog):
    chosen_sno = None

    def __init__(self, candidates, parent=None):
        ExtendableDialog.__init__(self, parent, remove_stretch=True)
        self.table_widget = QtGui.QTableWidget()
        self.table_widget.setAlternatingRowColors(True)
        self.table_widget.setSelectionBehavior(
            QtGui.QAbstractItemView.SelectRows)
        self.insertWidget(self.table_widget)

        headers = (_('Serialno'),
                   _('Status'),
                   _('Title'),
                   _('Forename'),
                   _('Surname'),
                   _('Birth Date'),
                   _('Address Line 1'),
                   _('Address Line 2'),
                   _('Town'),
                   _('POSTCODE'),
                   _('Tel1'),
                   _('Tel2'),
                   _('Mobile')
                   )

        self.table_widget.clear()
        self.table_widget.setSortingEnabled(False)
        self.table_widget.setRowCount(len(candidates))
        self.table_widget.setColumnCount(len(headers))
        self.table_widget.setHorizontalHeaderLabels(headers)
        self.table_widget.verticalHeader().hide()
        self.table_widget.horizontalHeader().setStretchLastSection(True)

        for row, candidate in enumerate(candidates):
            for col, attr in enumerate(candidate):
                if isinstance(attr, datetime.date):
                    item = QtGui.QTableWidgetItem(
                        localsettings.formatDate(attr))
                else:
                    item = QtGui.QTableWidgetItem(str(attr))
                self.table_widget.setItem(row, col, item)

        self.table_widget.setCurrentCell(0, 1)
        self.table_widget.setSortingEnabled(True)
        self.table_widget.sortItems(4)

        self.table_widget.itemDoubleClicked.connect(self.accept)

    def sizeHint(self):
        max_width = QtGui.QApplication.desktop().screenGeometry().width() - 100
        return QtCore.QSize(max_width, 400)

    def resizeEvent(self, event):
        widths = (0, 10, 15, 15, 15, 15, 20, 20, 20, 15, 10, 10, 10)
        sum_widths = sum(widths) + 30  # allow for vertical scrollbar
        for col in range(self.table_widget.columnCount()):
            col_width = widths[col] * self.width() / sum_widths
            self.table_widget.setColumnWidth(col, col_width)

    def exec_(self):
        if QtGui.QDialog.exec_(self):
            row = self.table_widget.currentRow()
            result = self.table_widget.item(row, 0).text()
            self.chosen_sno = int(result)
            return True
        return False

if __name__ == "__main__":

    localsettings.initiate()
    app = QtGui.QApplication([])

    dl = FindPatientDialog()
    print ("chosen sno = %s" % dl.chosen_sno)
    if dl.exec_():
        print (dl.chosen_sno)
