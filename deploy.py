#!/usr/bin/python3
#
# Copyright (C) 2019 Oleg Shnaydman
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#


import os
import argparse
import requests
import json
import re

DROPBOX_ERROR_CODE = 1
ZAPIER_ERROR_CODE = 2
TEMPLATE_ERROR_CODE = 3
CHANGES_ERROR_CODE = 4
OUTPUT_FILE_PARSING_ERROR = 5

DROPBOX_UPLOAD_ARGS = {
    'path': None,
    'mode': 'overwrite',
    'autorename': True,
    'strict_conflict': True
}
DROPBOX_SHARE_DATA = {
    'path': None,
    'settings': {
        'requested_visibility': 'public'
    }
}
DROPBOX_SHARE_FOLDER = {
    'path': None,
}
DROPBOX_DELETE_DATA = {
    'path' : None
}
DROPBOX_CREATE_FOLDER_DATA = {
    'path' : None
}

DROPBOX_UPLOAD_URL = 'https://content.dropboxapi.com/2/files/upload'
DROPBOX_CREATE_FOLDER_URL = 'https://api.dropboxapi.com/2/files/create_folder_v2'
DROPBOX_SHARE_URL = 'https://api.dropboxapi.com/2/sharing/create_shared_link_with_settings'
DROPBOX_DELETE_URL = 'https://api.dropboxapi.com/2/files/delete_v2'



ZAPIER_SEND_DATA = {
    'to': None,
    'subject': None,
    'body': None
}


def upload_to_dropbox(target_file_name, source_file, dropbox_token, dropbox_folder):
    '''Upload file to dropbox
    
    Args:
        target_file_name (str): Uploaded file will be rename to this file name.
        source_file (str): File that is going to be uploaded.
        dropbox_token (str): Dropbox API key.
        dropbox_folder (str): Dropbox target folder.

    Returns:
        str: Shared url for download.
    '''
    dropbox_path = '/{folder}/{file_name}'.format(folder=dropbox_folder, file_name=target_file_name)
    DROPBOX_UPLOAD_ARGS['path'] = dropbox_path
    DROPBOX_SHARE_DATA['path'] = dropbox_path
    DROPBOX_DELETE_DATA['path'] = dropbox_path

    # Try to delete the file before upload
    # It's possible to overwrite but this way is cleaner
    headers = {'Authorization': 'Bearer ' + dropbox_token,
            'Content-Type': 'application/json'}
    
    requests.post(DROPBOX_DELETE_URL, data=json.dumps(DROPBOX_DELETE_DATA), headers=headers)

    headers = {'Authorization': 'Bearer ' + dropbox_token,
               'Dropbox-API-Arg': json.dumps(DROPBOX_UPLOAD_ARGS),
               'Content-Type': 'application/octet-stream'}

    # Upload the file
    r = requests.post(DROPBOX_UPLOAD_URL, data=open(source_file, 'rb'), headers=headers)

    if r.status_code != requests.codes.ok:
        print("Failed: upload file to Dropbox: {errcode}".format(errcode=r.status_code))

    headers = {'Authorization': 'Bearer ' + dropbox_token,
               'Content-Type': 'application/json'}

    # Share and return downloadable url
    r = requests.post(DROPBOX_SHARE_URL, data=json.dumps(DROPBOX_SHARE_DATA), headers=headers)

    if r.status_code != requests.codes.ok:
        print("Failed: get share link from Dropbox {errcode}".format(errcode=r.status_code))

    # Replace the '0' at the end of the url with '1' for direct download
    return re.sub('dl=.*', 'raw=1', r.json()['url'])

def upload_to_dropbox(source_folder, dropbox_token, dropbox_folder, delete_folder):
    '''Upload file to dropbox
    
    Args:
        source_folder (str): Folder path where all the files be uploaded.
        dropbox_token (str): Dropbox API key.
        dropbox_folder (str): Dropbox target folder.

    Returns:
        str: Shared url for download.
    '''
    if (delete_folder):
        DROPBOX_DELETE_DATA['path'] = '/' + dropbox_folder
        headers = {'Authorization': 'Bearer ' + dropbox_token,
                'Content-Type': 'application/json'}
        
        r = requests.post(DROPBOX_DELETE_URL, data=json.dumps(DROPBOX_DELETE_DATA), headers=headers)
        if r.status_code != requests.codes.ok:
            print("Failed: create delete on Dropbox:{errcode}".format(errcode=vars(r)))

    headers = {'Authorization': 'Bearer ' + dropbox_token,
               'Content-Type': 'application/json'}
    DROPBOX_CREATE_FOLDER_DATA['path'] = '/'  + dropbox_folder
    r = requests.post(DROPBOX_CREATE_FOLDER_URL, data=json.dumps(DROPBOX_CREATE_FOLDER_DATA), headers=headers)
    if r.status_code != requests.codes.ok:
        print("Failed: create folder on Dropbox:{errcode}".format(errcode=vars(r)))

    dropbox_base_path = '/{folder}/'.format(folder=dropbox_folder)
    # TODO: delete files (is it necessary?)
    # # Try to delete the file before upload
    # # It's possible to overwrite but this way is cleaner
    # DROPBOX_DELETE_DATA['path'] = dropbox_folder
    # headers = {'Authorization': 'Bearer ' + dropbox_token,
    #         'Content-Type': 'application/json'}

    # delete_request = requests.post(DROPBOX_DELETE_URL, data=json.dumps(DROPBOX_DELETE_DATA), headers=headers)

    # if delete_request.status_code == 409:
    #     print("Folder does not exist, continue to upload.")
    # elif delete_request.status_code != requests.codes.ok:
    #     print("Failed: delete folder from Dropbox: {errcode}".format(errcode=delete_request.status_code))
    #     return None
    # else:
    #     print("Success deleted folder from Dropbox")

    for root, dirs, files in os.walk(source_folder):
        for filename in files:

            # construct the full local path
            local_path = os.path.join(root, filename)
            print("File path to upload: {path}".format(path=local_path))
            # construct the full Dropbox path
            relative_path = os.path.relpath(local_path, source_folder)
            dropbox_path = os.path.join(dropbox_base_path, relative_path) # absolute pth from folder to filename in dropbox

            # upload the file
            # with open(local_path, 'rb') as f:
            #     client.put_file(dropbox_path, f)

            # Upload the file
            DROPBOX_UPLOAD_ARGS['path'] = dropbox_base_path + filename
            headers = {'Authorization': 'Bearer ' + dropbox_token,
                       'Dropbox-API-Arg': json.dumps(DROPBOX_UPLOAD_ARGS),
                       'Content-Type': 'application/octet-stream'}

            r = requests.post(DROPBOX_UPLOAD_URL, data=open(local_path, 'rb'), headers=headers)

            if r.status_code != requests.codes.ok:
                print("Failed: upload file to Dropbox:{errcode}".format(errcode=vars(r)))

    # TODO: return share url
    #
    headers = {'Authorization': 'Bearer ' + dropbox_token, 'Content-Type': 'application/json'}
    DROPBOX_SHARE_FOLDER['path'] = dropbox_base_path
    # Share and return downloadable url
    r = requests.post("https://api.dropboxapi.com/2/sharing/share_folder", data=json.dumps(DROPBOX_SHARE_FOLDER), headers=headers)
    shared_folder_url = ""
    if r.status_code != requests.codes.ok:
        print("Failed: get share link from Dropbox {message}".format(message=r.json()["error"]))
        shared_folder_url = r.json()["error"]["bad_path"]['preview_url']
    else:
        print("Share url {url}".format(url=r.json()))
        shared_folder_url = r.json()['preview_url']

    return shared_folder_url


def send_email(zapier_hook, to, subject, body):
    '''Send email with zapier hook
    
    Args:
        zapier_hook (str): Zapier hook url.
        to (str): Email recipients separated by comma.
        subject (str): Email subject.
        body (str): Email body.

    Returns:
        bool: Send success/fail.
    '''
    ZAPIER_SEND_DATA['to'] = to
    ZAPIER_SEND_DATA['subject'] = subject
    ZAPIER_SEND_DATA['body'] = body

    headers = {'Content-Type': 'application/json'}

    r = requests.post(zapier_hook, data=json.dumps(ZAPIER_SEND_DATA), headers=headers)

    return r.status_code == requests.codes.ok


def get_app(release_dir):
    '''Extract app data
    
    Args:
        release_dir (str): Path to release directory.

    Returns:
        (str, str): App version and path to release apk file.
    '''
    output_path = os.path.join(release_dir, 'output.json')

    with(open(output_path)) as app_output:
        json_data = json.load(app_output)

    apk_details_key = ''
    if 'apkInfo' in json_data[0]:
        apk_details_key = 'apkInfo'
    elif 'apkData' in json_data[0]:
        apk_details_key = 'apkData'
    else:
        print("Failed: parsing json in output file")
        return None, None

    app_version = json_data[0][apk_details_key]['versionName']
    app_file = os.path.join(release_dir, json_data[0][apk_details_key]['outputFile'])
    return app_version, app_file


def get_target_file_name(app_name, app_version):
    '''Generate file name for released apk, using app name and version:
    app_name - MyApp
    version - 1.03
    result: myapp_1_03.apk
    
    Args:
        app_name (str): App name.
        app_version (str): App version.

    Returns:
        str: App file name.
    '''
    app_name = app_name.lower()
    app_version = app_version.replace('.', '_')
    return '{name}_{version}.apk'.format(name=app_name, version=app_version).replace(' ','')


def get_changes(change_log_path):
    '''Extract latest changes from changelog file.
    Changes are separated by ##

    Args:
        change_log_path (str): Path to changelog file.

    Returns:
        str: Latest changes.
    '''
    with(open(change_log_path)) as change_log_file:
        change_log = change_log_file.read()

    # Split by '##' and remove lines starting with '#'
    latest_version_changes = change_log.split('##')[0][:-1]
    latest_version_changes = re.sub('^#.*\n?', '', latest_version_changes, flags=re.MULTILINE)

    return latest_version_changes


def get_email(app_name, app_version, app_url, changes, template_file_path):
    '''Use template file to create release email subject and title.

    Args:
        app_name (str): App name.
        app_version (str): App version.
        app_url (str): Url for app download.
        changes (str): Lastest app changelog.
        template_file_path (str): Path to template file.

    Returns:
        (str, str): Email subject and email body.
    '''
    target_subject = 1
    target_body = 2
    target = 0

    subject = ''
    body = ''

    template = ''

    with(open(template_file_path)) as template_file:
        # Open template file and replace placeholders with data
        template = template_file.read().format(
            app_download_url=app_url,
            change_log=changes,
            app_name=app_name,
            app_version=app_version
        )
        
    # Iterate over each line and collect lines marked for subject/body
    for line in template.splitlines():
        if line.startswith('#'):
            if line.startswith('#subject'):
                target = target_subject
            elif line.startswith('#body'):
                target = target_body
        else:
            if target == target_subject:
                subject += line + '\n'
            elif target == target_body:
                body += line + '\n'
    
    return subject.rstrip(), body.rstrip()


if __name__ == '__main__':
    # Command line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('--release.dir', dest='release_dir', help='path to release folder', required=True)
    parser.add_argument('--app.name', dest='app_name', help='app name that will be used as file name', required=False)
    parser.add_argument('--changelog.file', dest='changelog_file', help='path to changelog file', required=False)
    parser.add_argument('--template.file', dest='template_file', help='path to email template file', required=False)
    parser.add_argument('--dropbox.token', dest='dropbox_token', help='dropbox access token', required=True)
    parser.add_argument('--dropbox.folder', dest='dropbox_folder', help='dropbox target folder', required=True)
    parser.add_argument('--dropbox.upload_folder', dest='dropbox_upload_folder', help='upload entire folder', required=False)
    parser.add_argument('--dropbox.delete_folder', dest='dropbox_delete_folder', help='delete folder before every upload', required=False)
    parser.add_argument('--zapier.hook', dest='zapier_hook', help='zapier email web hook', required=False)
    parser.add_argument('--email.to', dest='email_to', help='email recipients', required=False)
    parser.add_argument('--slack.webhook', dest='slack_webhook', help='slack webhook url', required=False)

    options = parser.parse_args()

    shared_folder_url = ""

    if (options.dropbox_upload_folder == None):
        # Extract app version and file
        app_version, app_file = get_app(options.release_dir)
        if app_version == None or app_file == None:
            exit(OUTPUT_FILE_PARSING_ERROR)
        
        target_app_file = get_target_file_name(options.app_name, app_version)

        # Upload app file and get shared url
        file_url = upload_to_dropbox(target_app_file, app_file, options.dropbox_token, options.dropbox_folder)
        if file_url == None:
            exit(DROPBOX_ERROR_CODE)
    else:
        delete_folder = False
        if (options.dropbox_delete_folder==None):
            delete_folder = True

        shared_folder_url = upload_to_dropbox(options.release_dir,options.dropbox_token, options.dropbox_folder, delete_folder)
        if shared_folder_url == None:
            exit(DROPBOX_ERROR_CODE)
    
    if options.changelog_file != None:
        # Extract latest changes
        latest_changes = get_changes(options.changelog_file)
        if latest_changes == None:
            exit(CHANGES_ERROR_CODE)
    
    if options.email_to != None:
        # Compose email subject and body
        subject, body = get_email(options.app_name, app_version, file_url, latest_changes, options.template_file)
        if subject == None or body == None:
            exit(TEMPLATE_ERROR_CODE)

        # Send email with release data
        if not send_email(options.zapier_hook, options.email_to, subject, body):
            exit(ZAPIER_ERROR_CODE)

    if options.slack_webhook != None:
        slack_headers = {'Content-Type': 'application/json'}

        json_data = {
            "text": "Your apk is ready for `{project_branch}` on {url}".format(project_branch=options.dropbox_folder,url=shared_folder_url),
        }
        r = requests.post(options.slack_webhook, data=json.dumps(json_data), headers=slack_headers)

        if r.status_code != requests.codes.ok:
            print("Failed to send slack webhook:{errcode}".format(errcode=vars(r)))
        else:
            print("Slack message sent")

    exit()