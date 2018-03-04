"""
submit_assignment.py

Submits a canvas assignment given a directory.
"""

from canvasapi import Canvas
from canvasapi.requester import Requester
from canvasapi.upload import Uploader
import os.path
import yaml
from enum import Enum
from glob import glob

class ConfigOptions(Enum):
    AID = "assignment_id"
    CID = "course_id"
    URL = "canvas_url"
    FILES = "files"
    API_KEY = "api_key"

class ConfigReader(object):

    def __init__(self, path, include_file = ".canvas-include.yml"):
        """
        Creates a ConfigReader which reads in the canvas include configuration
        and validates it.
        """

        self.path = path
        self.include_file = include_file

    def read(self):
        """
        Reads the configuration file from a given directory.
        """

        path = self.path
        include_file = self.include_file

        if not os.path.isdir(path):
            raise ValueError("'path' ({}) must be a directory.".format(path))

        include_file_path = os.path.join(path, include_file)

        if not os.path.isfile(include_file_path):
            raise FileNotFoundError("{} does not exist".format(
                include_file_path))

        with open(include_file_path, 'r') as f:
            canvas_config = yaml.load(f.read())

        self.config = canvas_config
        self.__validate_config()
        self._get_file_list()

        return self.config, self.file_list, self.zip_file_list

    def __validate_config(self):
        """
        Validates the configuration, making sure we have the necessary 
        information.
        """

        FIRST_LEVEL_KEYS = [opt.value for opt in list(ConfigOptions)]
        bad_keys = []

        for key in FIRST_LEVEL_KEYS:
            if not key in self.config.keys():
                bad_keys.append(key)

        if bad_keys:
            raise ValueError("""provided configuration 
                                file is missing 
                                required keys: {}""".format(bad_keys))

    def _get_file_list(self):
        """
        Gets an explicit file list to upload from the globs / list in our
        configuration.
        """

        files = self.config[ConfigOptions.FILES.value]
        globs_to_zip = []
        file_list = []
        zip_file_list = []

        for entry in files:
            if type(entry) == dict and "zip" in entry:
                globs_to_zip = entry["zip"]
                continue
            elif type(entry) == str:
                file_list.extend(glob(os.path.join(self.path, entry)))
            else:
                raise ValueError("unexpected type detected in file list")
        
        for entry in globs_to_zip:
            if type(entry) == str:
                zip_file_list.extend(glob(os.path.join(self.path, entry)))
            else:
                raise ValueError("unexpected type detected in zip file list")

        self.file_list = file_list
        self.zip_file_list = zip_file_list


class CanvasAssignment(object):

    def __init__(self, path, include_file = ".canvas-include.yml"):
        """
        Creates a CanvasAssignment object that will handle submissions of this
        assignment to Canvas. 'path' should be the path to an assignment 
        directory.

        :param path: path to the assignment directory
        :param include_file: the configuration file to look for in the 
                             assignment directory.
        """

        config, file_list, zip_file_list = ConfigReader(path, 
                                                        include_file).read()
        #   Add files
        self.file_list = file_list
        self.zip_file_list = zip_file_list

        #   Add configuration stuff
        self.assignment_id = config[ConfigOptions.AID.value]
        self.course_id = config[ConfigOptions.CID.value]
        url = config[ConfigOptions.URL.value]
        key = config[ConfigOptions.API_KEY.value]

        #   Add canvas stuff
        self._canvas = Canvas(url, key)
        self._requester = Requester(url, key)

        #   Add user ID stuff
        self.user_id = self._canvas.get_current_user().id
        print(self.user_id)

    def get_course(self):
        return self._canvas.get_course(self.course_id)

    def get_assignment(self):
        return self._canvas.get_course(
                self.course_id).get_assignment(self.assignment_id)

    def _zip_files(self):
        """
        Zips the files in self.zip_file_list and returns the path to the
        zip file.
        """

        pass

    def submit(self):
        """
        Uploads each new file to Canvas individually before submitting the
        newly uploaded files as a new submission.
        """

        file_ids = []
        for path in self.file_list:
            success, response = upload_file_to_assignment(
                    self._requester,
                    self.course_id,
                    self.assignment_id,
                    self.user_id,
                    path)
            if not success:
                raise IOError("Failed to upload {}.".format(path))
            file_ids.append(response["id"])

        submission = {}
        submission["file_ids"] = file_ids
        submission["submission_type"] = "online_upload"

        return self.get_assignment().submit(submission)
        

def upload_file_to_assignment(requester, course_id, assn_id, user_id, path):
    """
    Uploads the file found at path to the assignment indicated.
    """

    if not os.path.isfile(path):
        raise ValueError("'path' must be a valid path to a file.")

    unformatted_str = ("/api/v1/courses/{course_id}"
                       + "/assignments/{assignment_id}"
                       + "/submissions/{user_id}/files")
    upload_url = unformatted_str.format(course_id = course_id,
                                        assignment_id = assn_id,
                                        user_id = user_id)
    print(upload_url)
    print(path)
    return Uploader(requester, upload_url, path).start()


if __name__ == "__main__":
    pass
