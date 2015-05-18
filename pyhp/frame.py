from rpython.rlib import jit
from pyhp.datatypes import W_Reference


class Frame(object):
    _settled_ = True
    _immutable_fields_ = ['symbols', 'arguments[*]']
    _virtualizable_ = ['valuestack[*]', 'valuestack_pos', 'vars[*]']

    @jit.unroll_safe
    def __init__(self, interpreter, bytecode):
        from pyhp.bytecode import ByteCode
        assert(isinstance(bytecode, ByteCode))

        self = jit.hint(self, access_directly=True, fresh_virtualizable=True)
        self.valuestack = [None] * 10  # safe estimate!
        self.valuestack_pos = 0

        self.vars = [None] * bytecode.symbols().len()

        self.symbols = bytecode.symbols()

        # initialize superglobals like $_GET and $_POST
        for num, i in enumerate(bytecode.superglobals()):
            # if i is -1 superglobal is not used in the code
            if i >= 0:
                self.vars[i] = interpreter.superglobals[num]

    def push(self, v):
        pos = self.get_pos()
        len_stack = len(self.valuestack)

        # prevent stack overflow
        assert pos >= 0 and len_stack > pos

        self.valuestack[pos] = v
        self.valuestack_pos = pos + 1

    def pop(self):
        v = self.top()
        pos = self.get_pos() - 1
        assert pos >= 0
        self.valuestack[pos] = None
        self.valuestack_pos = pos
        return v

    @jit.unroll_safe
    def pop_n(self, n):
        if n < 1:
            return []

        r = []
        i = n
        while i > 0:
            i -= 1
            e = self.pop()
            r = [e] + r

        return r

    def top(self):
        pos = self.get_pos() - 1
        assert pos >= 0
        return self.valuestack[pos]

    def get_pos(self):
        return jit.promote(self.valuestack_pos)

    def _store(self, index, value):
        assert isinstance(index, int)
        assert index >= 0
        self.vars[index] = value

    def _load(self, index):
        assert isinstance(index, int)
        assert index >= 0
        return self.vars[index]

    def set_reference(self, name, index, value):
        assert isinstance(value, W_Reference)
        index = self._get_index(name, index)

        old_value = self._load(index)

        if not isinstance(old_value, W_Reference):
            self._store(index, value)
        else:
            old_value.put_value(value.get_value())

    def get_reference(self, name, index=-1):
        index = self._get_index(name, index)

        value = self._load(index)

        if not isinstance(value, W_Reference):
            value = W_Reference(value)
            self._store(index, value)

        return value

    def store_variable(self, name, index, value):
        index = self._get_index(name, index)

        old_value = self._load(index)

        if not isinstance(old_value, W_Reference):
            self._store(index, value)
        else:
            old_value.put_value(value)

    def get_variable(self, name, index=-1):
        index = self._get_index(name, index)
        value = self._load(index)

        if value is None:
            return None

        if not isinstance(value, W_Reference):
            return value

        return value.get_value()

    def _get_index(self, name, index):
        if index < 0:
            if self.symbols.contains(name):
                index = self.symbols.lookup(name)
            else:
                raise Exception(u'Frame has no variable %s' % name)
        return index

    def __repr__(self):
        return "Frame"
