class ImageValidationError(ValueError):
    """Base class for image-boundary validation failures."""


class ImageTooLargeError(ImageValidationError):
    pass


class UnsupportedImageError(ImageValidationError):
    pass


class InvalidImageError(ImageValidationError):
    pass
