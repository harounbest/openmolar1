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

'''
This module provides a function 'run' which will move data
to schema 2_7
'''
from __future__ import division

import datetime
import logging
import os
import sys

from openmolar.settings import localsettings
from openmolar.schema_upgrades.database_updater_thread import DatabaseUpdaterThread

LOGGER = logging.getLogger("openmolar")

SQLSTRINGS = [
'DROP TABLE IF EXISTS clinician_dates',
'DROP TABLE IF EXISTS diary_link',
'DROP TABLE IF EXISTS clinicians',
'''
CREATE TABLE clinicians (
  ix             smallint(5) unsigned not null auto_increment,
  initials       CHAR(5) NOT NULL,
  name           VARCHAR(64) NOT NULL,
  formal_name    VARCHAR(128) ,
  qualifications VARCHAR(64) ,
  type           smallint(5)  NOT NULL default 1,
  speciality     VARCHAR(64),
  data           VARCHAR(255),
  comments       VARCHAR(255),
  PRIMARY KEY (ix)
)
''',
'''
CREATE TABLE clinician_dates (
  clinician_ix           smallint(5) UNSIGNED NOT NULL,
  start_date             date NOT NULL,
  end_date               date,
  date_comments          VARCHAR(255),
  FOREIGN KEY (clinician_ix) REFERENCES clinicians(ix)
)
''',
'''
CREATE TABLE diary_link (
  clinician_ix       smallint(5) unsigned not null,
  apptix             smallint(5) unsigned not null,
  FOREIGN KEY (clinician_ix) REFERENCES clinicians(ix)
)
'''
]

# NOTE - if next statement fails, it is silently overlooked.
CLEANUPSTRINGS = [
]


PRACTITIONERS_QUERY = "select id, inits, apptix from practitioners"
DENTIST_DATA_QUERY = "select id,inits,name,formalname,fpcno,quals from practitioners where flag0=1"
APPTIX_QUERY = "select apptix,inits from practitioners where flag3=1"
ACTIVE_DENTS_QUERY = "select apptix, inits from practitioners where flag3=1 and flag0=1"
ACTIVE_HYGS_QUERY = "select apptix, inits from practitioners where flag3=1 and flag0=0"

SOURCE_QUERY = \
'select id, inits, apptix, name, formalname, fpcno, quals, flag0, flag3 from practitioners WHERE inits IS NOT NULL'

DEST_QUERY = \
'INSERT INTO clinicians (ix, initials, name, formal_name, qualifications, type, speciality, data, comments) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)'

GET_DATES_QUERY = 'select min(adate), max(adate) from aslot where apptix=%s'

ACTIVE_QUERY = '''INSERT INTO clinician_dates
(clinician_ix, start_date, end_date, date_comments)
VALUES (%s, %s, %s, %s)'''

DIARY_LINK_QUERY = 'INSERT INTO diary_link (clinician_ix, apptix) VALUES (%s, %s)'

class DatabaseUpdater(DatabaseUpdaterThread):

    def transfer_data(self):
        '''
        function specific to this update.
        '''
        self.cursor.execute(SOURCE_QUERY)
        rows = self.cursor.fetchall()
        for id, inits, apptix, name, formalname, fpcno, quals, flag0, flag3 in rows:
            self.cursor.execute(DEST_QUERY,
                (id,
                inits,
                name,
                formalname,
                quals,
                2 if flag0==0 else 1,
                None,
                "list_no=%s" % fpcno if fpcno else None,
                "transferred from practitioners table by 2_7 script")
                )
            appt_book_ix = apptix if apptix!=0 else id
            self.cursor.execute(GET_DATES_QUERY, (appt_book_ix,))
            start_date, end_date = self.cursor.fetchone()
            self.cursor.execute(ACTIVE_QUERY,
                (id,
                start_date,
                None if flag3==1 else end_date,
                "data generated by 2_7 script")
                )
            self.cursor.execute(DIARY_LINK_QUERY, (id, apptix))

    def run(self):
        LOGGER.info("running script to convert from schema 2.6 to 2.7")
        try:
            self.connect()
            #- execute the SQL commands
            self.progressSig(10, _("creating new tables"))
            self.execute_statements(SQLSTRINGS)

            self.progressSig(50, _("transferring data"))
            self.transfer_data()

            self.progressSig(95, _("executing cleanup statements"))
            self.execute_statements(CLEANUPSTRINGS)

            self.progressSig(97, _('updating settings'))
            LOGGER.info("updating stored database version in settings table")

            self.update_schema_version(("2.7",), "2_6 to 2_7 script")

            self.progressSig(100, _("updating stored schema version"))
            self.commit()
            self.completeSig(_("Successfully moved db to") + " 2.7")
            return True
        except Exception as exc:
            LOGGER.exception("error transfering data")
            self.rollback()
            raise self.UpdateError(exc)

if __name__ == "__main__":
    dbu = DatabaseUpdater()
    if dbu.run():
        LOGGER.info("ALL DONE, conversion successful")
    else:
        LOGGER.warning("conversion failed")
