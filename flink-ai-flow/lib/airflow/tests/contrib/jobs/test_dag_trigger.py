# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
import time
import unittest

import pendulum.datetime
from airflow.models.serialized_dag import SerializedDagModel

from airflow.contrib.jobs.dag_trigger import DagTrigger
from airflow.models import DagModel
from airflow.utils.mailbox import Mailbox
from airflow.utils.session import create_session
from tests.test_utils import db


class TestDagTrigger(unittest.TestCase):

    def setUp(self) -> None:
        db.clear_db_dags()
        db.clear_db_serialized_dags()

    def test_dag_trigger_is_alive(self):
        mailbox = Mailbox()
        dag_trigger = DagTrigger(".", -1, [], False, mailbox)
        assert not dag_trigger.is_alive()
        dag_trigger.start()
        time.sleep(1)
        assert dag_trigger.is_alive()
        dag_trigger.end()
        assert not dag_trigger.is_alive()

    def test_dag_trigger(self):
        mailbox = Mailbox()
        dag_trigger = DagTrigger(".", -1, [], False, mailbox)
        dag_trigger.start()
        type(self)._add_dag_needing_dagrun()

        message = mailbox.get_message()
        assert message.dag_id == "test"
        dag_trigger.end()

    def test_dag_trigger_parse_dag(self):
        mailbox = Mailbox()
        dag_trigger = DagTrigger("../../dags/test_scheduler_dags.py", -1, [], False, mailbox)
        dag_trigger.start()

        message = mailbox.get_message()
        # only one dag is executable
        assert "test_task_start_date_scheduling" == message.dag_id

        assert DagModel.get_dagmodel(dag_id="test_task_start_date_scheduling") is not None
        assert DagModel.get_dagmodel(dag_id="test_start_date_scheduling") is not None
        assert SerializedDagModel.get(dag_id="test_task_start_date_scheduling") is not None
        assert SerializedDagModel.get(dag_id="test_start_date_scheduling") is not None
        dag_trigger.end()

    @staticmethod
    def _add_dag_needing_dagrun():
        with create_session() as session:
            orm_dag = DagModel(dag_id="test")
            orm_dag.is_paused = False
            orm_dag.is_active = True
            orm_dag.next_dagrun_create_after = pendulum.now()
            session.merge(orm_dag)
            session.commit()
