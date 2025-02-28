import unittest
from unittest.mock import MagicMock
from care.im_wrapper import IMWrapper
from care.im_wrapper.whatsapp_bot import WhatsAppBot

class TestIMWrapper(unittest.TestCase):
    def setUp(self):
        self.care_api = MagicMock()
        self.im_wrapper = IMWrapper(self.care_api)

    def test_fetch_patient_records(self):
        patient_id = "example_patient_id"
        self.im_wrapper.fetch_patient_records(patient_id)
        self.care_api.fetch_patient_records.assert_called_once_with(patient_id)

    def test_fetch_current_medications(self):
        patient_id = "example_patient_id"
        self.im_wrapper.fetch_current_medications(patient_id)
        self.care_api.fetch_current_medications.assert_called_once_with(patient_id)

    def test_fetch_procedures(self):
        patient_id = "example_patient_id"
        self.im_wrapper.fetch_procedures(patient_id)
        self.care_api.fetch_procedures.assert_called_once_with(patient_id)

    def test_fetch_user_schedules(self):
        user_id = "example_user_id"
        self.im_wrapper.fetch_user_schedules(user_id)
        self.care_api.fetch_user_schedules.assert_called_once_with(user_id)

    def test_fetch_asset_status(self):
        asset_id = "example_asset_id"
        self.im_wrapper.fetch_asset_status(asset_id)
        self.care_api.fetch_asset_status.assert_called_once_with(asset_id)

    def test_fetch_inventory_data(self):
        inventory_id = "example_inventory_id"
        self.im_wrapper.fetch_inventory_data(inventory_id)
        self.care_api.fetch_inventory_data.assert_called_once_with(inventory_id)

class TestWhatsAppBot(unittest.TestCase):
    def setUp(self):
        self.im_wrapper = MagicMock()
        self.whatsapp_bot = WhatsAppBot(self.im_wrapper)

    def test_fetch_patient_records(self):
        patient_id = "example_patient_id"
        self.whatsapp_bot.fetch_patient_records(patient_id)
        self.im_wrapper.fetch_patient_records.assert_called_once_with(patient_id)

    def test_fetch_current_medications(self):
        patient_id = "example_patient_id"
        self.whatsapp_bot.fetch_current_medications(patient_id)
        self.im_wrapper.fetch_current_medications.assert_called_once_with(patient_id)

    def test_fetch_procedures(self):
        patient_id = "example_patient_id"
        self.whatsapp_bot.fetch_procedures(patient_id)
        self.im_wrapper.fetch_procedures.assert_called_once_with(patient_id)

    def test_fetch_user_schedules(self):
        user_id = "example_user_id"
        self.whatsapp_bot.fetch_user_schedules(user_id)
        self.im_wrapper.fetch_user_schedules.assert_called_once_with(user_id)

    def test_fetch_asset_status(self):
        asset_id = "example_asset_id"
        self.whatsapp_bot.fetch_asset_status(asset_id)
        self.im_wrapper.fetch_asset_status.assert_called_once_with(asset_id)

    def test_fetch_inventory_data(self):
        inventory_id = "example_inventory_id"
        self.whatsapp_bot.fetch_inventory_data(inventory_id)
        self.im_wrapper.fetch_inventory_data.assert_called_once_with(inventory_id)

if __name__ == "__main__":
    unittest.main()
