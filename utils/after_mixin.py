# utils/after_mixin.py


class AfterManagerMixin:
    """Mixin que registra callbacks `after/after_idle` e cancela no dispose()."""

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self._after_ids: set[str] = set()

    def after(self, delay_ms, callback=None, *args):  # type: ignore[override]
        if callback is None:
            return super().after(delay_ms)
        aid = super().after(delay_ms, callback, *args)
        try:
            self._after_ids.add(aid)
        except Exception:
            pass
        return aid

    def after_idle(self, callback, *args):  # type: ignore[override]
        aid = super().after_idle(callback, *args)
        try:
            self._after_ids.add(aid)
        except Exception:
            pass
        return aid

    def after_cancel(self, aid):  # type: ignore[override]
        try:
            self._after_ids.discard(aid)
        except Exception:
            pass
        return super().after_cancel(aid)

    def schedule(self, delay_ms: int, callback, *args, **kwargs):
        return self.after(delay_ms, callback, *args, **kwargs)

    def dispose(self):
        for aid in list(self._after_ids):
            try:
                self.after_cancel(aid)
            except Exception:
                pass
        self._after_ids.clear()

    def destroy(self):  # type: ignore[override]
        try:
            self.dispose()
        except Exception:
            pass
        return super().destroy()
