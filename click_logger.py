import os

class ClickLogger:
    """Class to log the user's click stream by storing the XPath of the clicked elements in a file."""

    def __init__(self, log_file_path: str):
        """Initialize the ClickLogger with the log file path."""
        self.log_file_path = log_file_path
        assert self.log_file_path, "Log file path should not be empty"
        self.log_file = None
        self.initialize_log_file()

    def initialize_log_file(self):
        """Initialize the log file if it doesn't exist."""
        if not os.path.exists(self.log_file_path):
            with open(self.log_file_path, 'w') as f:
                f.write("XPath\n")

    def log_click(self, xpath: str):
        """Log the user's click stream by writing the XPath of the clicked element to the log file."""
        assert xpath, "XPath should not be empty"
        with open(self.log_file_path, 'a') as f:
            f.write(xpath + '\n')
