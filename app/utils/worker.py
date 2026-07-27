from PySide2.QtCore import QObject, QThread, Signal


class WorkerSignals(QObject):
    """Signals for background task status and results."""
    finished = Signal(object)
    error = Signal(Exception)


class WorkerThread(QThread):
    """Generic QThread for running long-running operations in the background."""
    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()

    def run(self):
        try:
            result = self.fn(*self.args, **self.kwargs)
            self.signals.finished.emit(result)
        except Exception as e:
            self.signals.error.emit(e)


def run_in_background(fn, *args, on_success=None, on_error=None, **kwargs):
    """Helper to launch `fn(*args, **kwargs)` in a background thread.
    
    `on_success(result)` and `on_error(exception)` will be called on the Qt main GUI thread.
    """
    thread = WorkerThread(fn, *args, **kwargs)
    
    # Keep reference on parent if needed, but Qt signals handle cross-thread slot execution safely.
    if on_success:
        thread.signals.finished.connect(on_success)
    if on_error:
        thread.signals.error.connect(on_error)
        
    thread.finished.connect(thread.deleteLater)
    thread.start()
    return thread
