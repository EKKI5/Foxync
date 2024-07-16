class File:
    def __init__(self, is_dir = 0, file_rel_path = 0, content_bytes = 0, hash_var = 0):
        self.is_dir = is_dir
        self.file_rel_path = file_rel_path
        self.content_bytes = content_bytes
        self.hash = hash_var

    def to_json(self):
        """
        Convert the File object to a JSON-serializable dictionary.

        Returns:
        A dictionary representation of the File object.
        """
        return {
            "is_dir": self.is_dir,
            "file_rel_path": self.file_rel_path,
            "content_bytes": self.content_bytes,
            "hash": self.hash
        }

    @classmethod
    def to_object(self, file_dict):
        """
        Create a File object from a dictionary.

        Parameters:
        file_dict -- A dictionary containing the File data as dictionary.

        Returns:
        File object
        """

        return File(file_dict["is_dir"], file_dict["file_rel_path"], file_dict["content_bytes"], file_dict["hash"])