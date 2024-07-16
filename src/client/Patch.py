from File import File

import logging
from Logs import Logs

class Patch(File):

    def __init__(self, is_dir = 0, file_rel_path = 0, content_bytes = 0, hash_var = 0, patch = 0):
        """
        Initialize a new Patch object.
        
        Parameters:
        is_dir (int): Indicator if this block is a directory.
        file_rel_path (str): The relative path of the file this block belongs to.
        content_bytes (bytes): The content bytes of the block.
        hash_var (str): The hash of the block.
        patch (str): The patch of the block.
        """
        self.patch = patch

        super().__init__(is_dir, file_rel_path, content_bytes, hash_var)

    def to_json(self):
        """
        Convert the Block object to a JSON-serializable dictionary.

        Returns:
        A dictionary representation of the Block object.
        """
        Logs().write_new_log(logging.INFO, "SERIALIZING PATCH TO JSON")

        return {
            'is_dir': self.is_dir,
            'file_rel_path': self.file_rel_path,
            'content_bytes': self.content_bytes,
            'hash': self.hash,
            'patch': self.patch
        }

    @classmethod
    def to_object(self, patch_dict):
        """
        Create a Patch object from a dictionary.

        Parameters:
        patch_dict: A dictionary containing the Patch data as dictionary.

        Returns:
        A Patch object created from the provided dictionary.
        """
        Logs().write_new_log(logging.INFO, "CREATING PATCH AS OBJECT")
        return Patch(patch_dict['is_dir'], patch_dict['file_rel_path'], patch_dict['content_bytes'], patch_dict['hash'], patch_dict['patch'])