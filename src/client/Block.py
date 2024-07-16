from File import File
import logging
from Logs import Logs

class Block(File):
    """
    The Block class represents a block of data in a file system, inheriting from the File class.
    It includes additional attributes specific to blocks such as block number, starting byte, and block size.
    """

    def __init__(self, is_dir=0, file_rel_path=0, content_bytes=0, block_number=0, hash_var=0, starting_byte=0, block_size=0):
        """
        Initialize a new Block object.
        
        Parameters:
        is_dir -- Indicator if this block is a directory.
        file_rel_path -- The relative path of the file this block belongs to.
        content_bytes -- The content bytes of the block.
        block_number -- The block number within the file.
        hash_var -- The hash of the block.
        starting_byte -- The starting byte position of this block within the file.
        block_size -- The size of the block.
        """
        self.block_number = block_number
        self.starting_byte = starting_byte
        self.block_size = block_size

        # Call the constructor of the parent class File
        super().__init__(is_dir, file_rel_path, content_bytes, hash_var)

    def to_json(self):
        """
        Convert the Block object to a JSON-serializable dictionary.

        Returns:
        A dictionary representation of the Block object.
        """
        return {
            "is_dir": self.is_dir,
            "file_rel_path": self.file_rel_path,
            "content_bytes": self.content_bytes,
            "block_number": self.block_number,
            "hash": self.hash,
            "starting_byte": self.starting_byte,
            "block_size": self.block_size
        }

    @classmethod
    def to_object(cls, block_dict):
        """
        Create a Block object from a dictionary.

        Parameters:
        block_dict -- A dictionary containing the Block  data as dictionary.

        Returns:
        A Block object created from the provided dictionary.
        """
        Logs().write_new_log(logging.INFO, "CREATING BLOCK AS OBJECT")
        return cls(block_dict["is_dir"], block_dict["file_rel_path"], block_dict["content_bytes"], block_dict["block_number"], block_dict["hash"], block_dict["starting_byte"], block_dict["block_size"])