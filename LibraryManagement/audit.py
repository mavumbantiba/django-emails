from auditlog.registry import auditlog

from .models import Book, BookLoan


auditlog.register(Book)
auditlog.register(BookLoan)
