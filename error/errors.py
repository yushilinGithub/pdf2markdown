#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
errors
"""


class Error(Exception):
    """
    Error
    """

    code: int
    message: str
    e: Exception

    def __init__(self, code: int, message: str, exception: Exception):
        self.code = code
        self.message = message
        self.e = exception
    
    def __str__(self):
        if self.e is not None:
            return f"[Code:{self.code}]{self.message}, {str(self.e)}"
        return f"[Code:{self.code}]{self.message}"

    def with_error(self, exception: Exception):
        """
        with_error
        """
        return Error(self.code, self.message, exception)



class RetryableException(Error):
    """
    RetryableException
    """
    
    def with_error(self, exception: Exception):
        """
        with_error
        """
        return RetryableException(self.code, self.message, exception)


class UploadBosException(Exception):
    """
    update bos exception
    """
    pass


class FileUrlException(Exception):
    """
    file url error
    """
    pass


class RepeatedParseException(Error):
    """
    RepeatedParseException
    """
    pass

class ScanPdfException(Exception):
    """
    RepeatedParseException
    """
    pass