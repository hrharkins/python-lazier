class Singleton(str):
    pass
VOLATILE = Singleton('VOLATILE')    

def lazy(fn=None, name=None, method=False):
    '''
    >>> class MyClass(object):
    ...     @lazy
    ...     def x(self):
    ...         print("Creating")
    ...         return 'x'
    
    >>> obj = MyClass()
    >>> obj.x
    Creating
    'x'
    >>> obj.x
    'x'
    
    >>> class OtherClass(object):
    ...     @lazy('x')
    ...     def get_x(self):
    ...         print("Creating")
    ...         return 'x'
    >>> obj = OtherClass()
    >>> obj.x
    Creating
    'x'
    >>> obj.x
    'x'
    >>> obj.get_x()
    Creating
    'x'
    
    >>> class Base(object):
    ...     @lazy('x', method=True)
    ...     def get_x(self):
    ...         raise NotImplementedError('No x here')
    
    >>> class Subclass(Base):
    ...     def get_x(self):
    ...         print("Creating")
    ...         return 'x'
    
    >>> obj = Subclass()
    >>> obj.x
    Creating
    'x'
    >>> obj.x
    'x'
    
    '''
    
    if fn is None:
        def builder(fn):
            return lazy(fn, name=name, method=method)
        return builder            
    elif isinstance(fn, str):
        def builder(fn, name=fn):
            return lazy(fn, name=name, method=method)
        return builder            
    else:
        if name is None and name != fn.__name__:
            name = fn.__name__
        if method:            
            def src(obj, cls=None, name=fn.__name__ if method is True else method):
                return getattr(obj, name)()
        else:
            src = fn            
        def getter(self, obj, cls=None, name=name, VOLATILE=VOLATILE, src=src):
            if cls is None:
                return self
            else:
                result = src(obj)
                if result is not VOLATILE:
                    setattr(obj, name, result)
                return result
        getter.__name__ = name
        clsdict = { '__get__': getter, '__doc__': fn.__doc__ }
        if name == fn.__name__:
            return type(name, (), clsdict)()
        else:            
            def configure_class_for_lazy(self, cls, fn_name, name=name):
                setattr(cls, name, type(name, (), clsdict)())
                setattr(cls, fn.__name__, fn)
            clsdict['__set_name__'] = configure_class_for_lazy
            return type(name, (), clsdict)()
