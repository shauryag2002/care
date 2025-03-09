class WhatsAppBot:
    def __init__(self, im_wrapper):
        self.im_wrapper = im_wrapper

    def fetch_patient_records(self, patient_id):
        return self.im_wrapper.fetch_patient_records(patient_id)

    def fetch_current_medications(self, patient_id):
        return self.im_wrapper.fetch_current_medications(patient_id)

    def fetch_procedures(self, patient_id):
        return self.im_wrapper.fetch_procedures(patient_id)

    def fetch_user_schedules(self, user_id):
        return self.im_wrapper.fetch_user_schedules(user_id)

    def fetch_asset_status(self, asset_id):
        return self.im_wrapper.fetch_asset_status(asset_id)

    def fetch_inventory_data(self, inventory_id):
        return self.im_wrapper.fetch_inventory_data(inventory_id)
