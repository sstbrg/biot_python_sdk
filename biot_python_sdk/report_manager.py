from datetime import datetime
import json
import urllib.parse
import requests

class ReportManager:
    """
      The ReportManager class provides functionality for exporting, retrieving, and posting configuration snapshots of various entities using the report system.
      It handles data for devices and generic entities, allowing for the export of reports, transfer of configurations across organizations, and updates
      of references between entities.

      Attributes:
      - data_mgr: An instance of the data manager class responsible for interacting with the backend API.
      - configuration_template_names (list): A list of template names used for  configuration.
      - back_reference_mapping (dict): A mapping of entities to their back references, used for updating references after posting. key: back back refernced template. value: (refrenced template,refrence attribute name)
      - reference_to_copy_dict (dict): A dictionary defining the mapping between entities and the references that need to be copied what coping configurations between oranizations.
      - ge_post_order (tuple): The order in which generic entities should be posted to ensure dependencies are met.
      """

    def __init__(self,data_mgr):
        self.data_mgr = data_mgr
        self.configuration_template_names = ['sensor','patch','montage_configuration','channel','calibration_step']
        self.back_reference_mapping = {'patch': [('montage_configuration','patch')], 'montage_configuration': [('channel','montage_configuration'),('calibration_step','montage_calibraterd')]}
        self.reference_to_copy_dict = {'channel':'montage_configuration','calibration_step': 'montage_calibraterd'}
        self.ge_post_order = ('sensor', 'patch', 'montage_configuration',  'calibration_step','channel')
    def export_snapshot_by_entities(self,report_name,ge_template_names_to_filt, save_devices=False,start_date = "2024-05-01T09:03:33Z"):
        """
        Generates and exports a snapshot of data entities based on specified templates and a date range.

        Parameters:
        - report_name (str): The name of the report to be generated.
        - ge_template_names_to_filt (list): A list of template names used to filter the generic entities.
        - save_devices (bool, optional): A flag to indicate whether device data should be included in the report. Defaults to False.
        - start_date (str, optional): The start date for the data filter in ISO 8601 format. Defaults to "2024-05-01T09:03:33Z".

        Returns:
        - response: The response from the server after making the authenticated request to create the data report.
        """
        ge_template_id_to_filt = self.data_mgr._get_template_id_from_name(ge_template_names_to_filt)
        today_date=  datetime.now().isoformat()
        queries=[]
        query=dict()
        filter_dict =dict()
        filter_dict['_templateId']={'in':ge_template_id_to_filt}
        filter_dict['_creationTime'] = {"in": [],"from": start_date,"to": today_date,"notIn": [],"filter": {}}
        query["dataType"] = "generic-entity"
        query["filter"] = filter_dict
        queries.append(query)
        if save_devices:
            device_template_id =self.data_mgr._get_template_id_from_name('androidgateway')
            query = dict()
            filter_dict = dict()
            filter_dict['_templateId'] = {'eq': device_template_id}
            filter_dict['_creationTime'] = {"in": [], "from": start_date, "to": today_date, "notIn": [], "filter": {}}
            query["dataType"] = "device"
            query["filter"] = filter_dict
            queries.append(query)

        body_dict =dict()
        body_dict['outputMetadata']={'exportFormat' :'JSON'}
        body_dict['queries'] = queries
        body_dict['name'] = report_name
        response = self.data_mgr._make_authenticated_request(CREATE_DATA_REPORT_URL, method="POST", json=body_dict)
        return response

    def export_full_configuration_snapshot(self, report_name, start_date="2024-05-01T09:03:33Z"):
        """
        A wrapper function for 'export_snapshot_by_entities' that exports the full configuration snapshot.

        Parameters:
        - report_name (str): The name of the report to be generated.
        - start_date (str, optional): The start date for the data filter in ISO 8601 format. Defaults to "2024-05-01T09:03:33Z".

        Returns:
        - response: The response from the server after making the authenticated request to create the data report.
        """
        return self.export_snapshot_by_entities( report_name, self.configuration_template_names,save_devices=True, start_date = start_date)

    def get_report_file_by_name(self,report_name):
        """
                Retrieves the report file by its name.

                Parameters:
                - report_name (str or list): The name(s) of the report(s) to be retrieved.

                Returns:
                - reports_data_dict (dict): A dictionary containing the report data, where the keys are report types (e.g., 'device', 'generic-entity') and the values are the report data in JSON format.
        """
        if type(report_name)==str:
            filter_type = 'eq'
        elif type(report_name) is list:
            filter_type = 'in'
        else:
            print('Template name is not str or list')
            return None
        search_request = {"filter": {"name": {f"{filter_type}": report_name}}}
        search_request_encoded = urllib.parse.quote(json.dumps(search_request))
        response = self.data_mgr._make_authenticated_request(f"{GET_DATA_REPORT_URL}?searchRequest={search_request_encoded}")
        reports_data_dict = dict()
        if response:
            reports=response.json()['data']
            if len(reports)>1:
                raise Exception('More Than One report with this name.')
            for report in reports:
                for key in report['fileOutput']['filesLocation'].keys():
                    report_paths=report['fileOutput']['filesLocation'][key]['paths']
                    for path in report_paths:
                        response=requests.get(path)
                        if response.status_code==200:
                            reports_data_dict[key] = response.json()
            return reports_data_dict

    def post_full_configuration_report(self,report_dict):
        """
        Posts the full configuration data (retrieved from a report) to the server.

        Parameters:
        - report_dict (dict): The dictionary containing the report data to be posted, typically retrieved from the `get_report_file_by_name` method.

        Returns:
        - None. (Prints the response from the server for each posted entity.)

        Usage:
        This method is used to post a full configuration report back to the server. It handles both device and
        generic entity data. It first checks if there are 'device' entities in the report, then posts them. After
        that, it processes 'generic-entity' data in a specific order: 'sensor', 'patch', 'montage_configuration',
        'calibration_step', and 'channel'.
        """
        if 'device' in report_dict.keys():
             self.post_report_json(report_dict['device'], template_type='device') # todo define device logic.
        if 'generic-entity' in report_dict.keys():
            ge_report= report_dict['generic-entity']
            #ge_post_order = ( 'patch', 'montage_configuration', 'channel', 'calibration_step')
            for template_name in self.ge_post_order:
                current_template_entities = [ge for ge in ge_report if ge['_template']['name']==template_name]
                lookup_table = self.post_report_json(current_template_entities, template_type='generic-entity')
                if template_name in self.back_reference_mapping.keys():
                    for ref in self.back_reference_mapping[template_name]:
                        ge_report = self.update_report_by_reference_lookuptable(lookup_table,ge_report,ref[1],ref[0])

    def post_report_json(self,report_data,template_type):
        """
                Posts a single report (either device or generic entity) in JSON format to the server.

                Parameters:
                - report_data (list): The list of entities to be posted, extracted from the report.
                - template_type (str): The type of template ('device' or 'generic-entity') that is being posted.

                Returns:
                - None. (Prints the response from the server for each posted entity.)

                Usage:
                This method is a helper function used by `post_full_configuration_report` to post individual entities to
                the server, either as devices or generic entities. Depending on the `template_type`, it handles the
                JSON structure differently for devices and generic entities.
        """
        lookup_table = {}
        post_json = dict()
        for entity in report_data:
            if 'full_patch_json' in entity.keys():
                del entity['full_patch_json'] # work around for get montages plugin.
            if entity['_template']['name']=='montage_configuration':
                if 'montage_image' in entity.keys():
                    del entity['montage_image']
            if entity['_template']['name']=='sensor':
                if 'device' in entity.keys():
                    del entity['device']
            for key in entity.keys():
                post_json['_templateId'] = entity['_template']['id']
                post_json['_ownerOrganization'] = {'id':entity['_ownerOrganization']['id']}
                if template_type=='device':
                    post_json['_id'] = entity['_id']
                    post_json['_configuration']=entity['_configuration']
                    post_json['_timezone'] = entity['_timezone']
                else:
                    post_json['_name'] = entity['_name']
                if key[0]!='_': # not built in attribute
                    if type(entity[key])==dict:
                        post_json[key] = {'id':entity[key]['id']}
                    else:
                        post_json[key] = entity[key]
            if template_type=='device':
                response = self.data_mgr._make_authenticated_request(endpoint=DEVICES_URL, method='POST', json=post_json)
            if template_type == 'generic-entity':
                response = self.data_mgr._make_authenticated_request(endpoint=GENERIC_ENTITES_URL, method='POST',json=post_json)
            print(response,':' ,response.content)
            if response:
                lookup_table[entity['_id']]=response.json()['_id']
        return lookup_table

    def config_report_to_different_org(self,src_org_id,new_org_id,report_data_dict):
        """
            Configures a report to be associated with a different organization.

            This method takes a report data dictionary and modifies it so that the ownership of all entities
            within the report is transferred from one organization to another. It iterates over each entity
            in the report, checks if it belongs to the source organization, and if so, changes its
            ownership to the new organization.

            Parameters:
            - src_org_id (str): The ID of the source organization whose entities are being transferred.
            - new_org_id (str): The ID of the new organization to which the entities will be assigned.
            - report_data_dict (dict): A dictionary containing the report data, typically structured by
              entity type (e.g., 'device', 'generic-entity').

            Returns:
            - new_report_dict (dict): A new dictionary with the updated report data, where the ownership
              of entities is transferred to the new organization.
        """
        new_report_dict = {key: [] for key in report_data_dict.keys()}
        for key in report_data_dict.keys():
                for i in  range(len(report_data_dict[key]) - 1, -1, -1):
                    e = report_data_dict[key][i]
                    if e['_ownerOrganization']['id'] == src_org_id:
                        if  type(new_report_dict[key])==list:
                            new_report_dict[key].append(e)
                            new_report_dict[key][-1]['_ownerOrganization'] = {'id':new_org_id}
                    if key=='device':
                        #new_report_dict[key][-1]['_id']='Z'+new_report_dict[key][-1]['_id'][1:]
                        new_report_dict['device'] = {} #todo define device copy logic
        return new_report_dict

    def full_org_transfer_wrapper(self,src_org_id,dst_org_id,report_name,assests_to_assign_dict=None):
        """
            Transfers an entire organization configuration to another organization.

            This method serves as a wrapper that handles the full process of transferring all entities and
            configurations from one organization to another. It retrieves the report data by its name,
            reconfigures the ownership to the destination organization, filters the report data based on
            specified assets, and finally posts the full configuration to the new organization.

            Parameters:
            - src_org_id (str): The ID of the source organization.
            - dst_org_id (str): The ID of the destination organization.
            - report_name (str): The name of the report to retrieve and transfer.
            - assets_to_assign_dict (dict, optional): A dictionary specifying which assets to assign during
              the transfer. This parameter is used to filter the report data.

            Returns:
            - None. The method posts the configuration to the new organization.
        """
        report_data_dict = self.get_report_file_by_name(report_name)
        report_data_dict = self.config_report_to_different_org(src_org_id, dst_org_id, report_data_dict)
        if assests_to_assign_dict:
            report_data_dict = self.filter_report_for_copy(report_data_dict, assests_to_assign_dict)
        self.post_full_configuration_report(report_data_dict)

    def filter_report_for_copy(self,report_data_dict,copy_dict):
        for i in range(len(report_data_dict['generic-entity']) - 1, -1, -1):
            r=report_data_dict['generic-entity'][i]
            if 'EEG4_FC'==r['_name']:
                pass
            if r['_template']['name'] in copy_dict.keys():
                if r['_name'] not in copy_dict[r['_template']['name']]:
                    report_data_dict['generic-entity'].pop(i)
            else:
                has_ref_to_copy =False
                if r['_template']['name'] in self.reference_to_copy_dict.keys():
                    if self.reference_to_copy_dict[r['_template']['name']] in r.keys():
                        if r[self.reference_to_copy_dict[r['_template']['name']]] is not None:
                            if r[self.reference_to_copy_dict[r['_template']['name']]]['name'] in copy_dict[r[self.reference_to_copy_dict[r['_template']['name']]]['templateName']]:
                                has_ref_to_copy = True

                if not has_ref_to_copy:
                    report_data_dict['generic-entity'].pop(i)
        return report_data_dict

    def update_report_by_reference_lookuptable(self,lookup_table,report_data,reference_name,template_name):
        """
            Updates report data by replacing references with IDs from a lookup table.

            This method iterates through the report data and updates any references within entities based
            on a provided lookup table. It replaces the referenced entity's ID with the corresponding ID
            from the lookup table.

            Parameters:
            - lookup_table (dict): A dictionary mapping old IDs to new IDs.
            - report_data (list): A list of entities in the report that need to be updated.
            - reference_name (str): The name of the reference field to update.
            - template_name (str): The template name of the entities to be updated.

            Returns:
            - report_data (list): The updated list of entities with references replaced by new IDs from
              the lookup table.
        """
        for i,r in enumerate(report_data):
            if r['_template']['name']==template_name:
                if reference_name in r.keys():
                    if r[reference_name]:
                        report_data[i][reference_name]['id'] = lookup_table[r[reference_name]['id']]
        return report_data

