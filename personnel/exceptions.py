# personnel/exceptions.py

class BorrowingError(Exception):
    """Erreur générique lors d'une tentative d'emprunt."""
    pass

class MediaNotAvailable(BorrowingError):
    pass

class MaxBorrowLimitReached(BorrowingError):
    pass

class MediaAlreadyBorrowed(BorrowingError):
    pass

class InvalidReturnOperation(BorrowingError):
    pass
