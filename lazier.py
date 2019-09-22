'''
Lazier

Allows for calculation of class members on demand.  Members can be derived from
methods or other attributes/methods.  Once calculated, lazily computed values
remain with the object until deleted.

Basic Usage:

>>> class MyClass(object):
...     @lazy                   # Optional () without arguments
...     def x(self):
...         print("Creating")
...         return 'x'

>>> obj = MyClass()
>>> obj.x
Creating
'x'
>>> obj.x
'x'
'''

import sys, abc

if sys.version_info >= (3, 6):
    def if_python_36_or_newer():
        '''
        Specifying the attribute name to use (Python 3.6 or later):

        >>> class OtherClass(object):
        ...     @lazy(name='x')             # Or simply lazier.lazy('x')
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

        Specifying a factory method (Python3.6 or later:

        >>> class Base(object):
        ...     @lazy(name='x', method=True)
        ...     def get_x(self):
        ...         return 'base_x'

        >>> class Subclass(Base):
        ...     def get_x(self):
        ...         print("Creating")
        ...         return 'x from ' + super().get_x()

        >>> obj = Subclass()
        >>> obj.x
        Creating
        'x from base_x'
        >>> obj.x
        'x from base_x'

        '''

class Singleton(str):
    pass
VOLATILE = Singleton('VOLATILE')    

def lazy(fn=None, name=None, method=False):
    if fn is None:
        # If fn wasn't specified this is a zero-argument use, lazy(). so the 
        # function will be passed to the builder function.
        def builder(fn):
            return lazy(fn, name=name, method=method)
        return builder

    elif isinstance(fn, str):
        # If fn is a string, it's really specifying the property name.  Again,
        # a function will be passed to the builder, but we'll use the fn 
        # argument as the name.
        def builder(fn, name=fn):
            return lazy(fn, name=name, method=method)
        return builder

    elif callable(fn):
        # Only callable types may pass.

        if name is None and name != fn.__name__:
            # If a name was passed (and not the function name0, use that for the
            # name.
            name = fn.__name__

        if method:            
            # If method is not false, it's either simply True or the name of
            # the method to invoke when retrieving the value.
            def src(obj, cls=None, name=fn.__name__ if method is True else method):
                return getattr(obj, name)()
        else:
            # Method is falsy, so the source is the fn passed.
            src = fn            

        # Now for the actual get function for the property.
        def getter(self, obj, cls=None, name=name, VOLATILE=VOLATILE, src=src):
            if cls is None:
                # Without a second argument, obj is the class.  This usually means
                # that we are being probed by pydoc or other introspection.
                return self
            else:
                # Otherwise, get the result.  If it is not VOLATILE, store it
                # in the object's __dict__, which will then be offered when the
                # attribute is accessed.
                result = src(obj)
                if result is not VOLATILE:
                    setattr(obj, name, result)
                return result

        # Setup the getter's pydoc information.
        #:getter.__name__ = name

        # Prepare to make a singleton class whose sole instance will be the 
        # property.
        clsdict = { '__get__': getter, '__doc__': fn.__doc__ }
        if name == fn.__name__:
            # If name wasn't something different, we can go ahead and make
            # the singleton.
            return type(name, (), clsdict)()
        else:            
            # Otherwise, the property should be used on a different name.  This
            # requires Python3.7 to support the __set_name__ magic method.
            def configure_class_for_lazy(self, cls, fn_name, name=name):
                setattr(cls, name, type(name, (), clsdict)())
                setattr(cls, fn.__name__, fn)
            clsdict['__set_name__'] = configure_class_for_lazy
            return type(name, (), clsdict)()

    else:
        # The fn isn't a valid type.  Bomb out.
        raise TypeError('Attempt to use %r as a lazy function' % fn)

class APINoABC(object):
    '''
    >>> class MyAPI(API):
    ...     def greet(self):
    ...         return 'hello'

    >>> class APIer(object):
    ...     myapi = MyAPI.from_method('get_myapi')
    ...     def get_myapi(self):
    ...         return None

    >>> APIer().myapi
    Traceback (most recent call last):
      ...
    ValueError: API None is not a MyAPI

    >>> class BetterAPIer(APIer):
    ...     def get_myapi(self):
    ...         print('building api')
    ...         return MyAPI()

    >>> better_apier = BetterAPIer()
    >>> better_apier.myapi.greet()
    building api
    'hello'
    '''

    @classmethod
    def from_method(cls, name, prop=False):
        return cls.Locator(cls, lambda t: getattr(t, name, None)())

    @classmethod
    def from_property(cls, name, prop=False):
        return cls.Locator(cls, lambda t: getattr(t, name, None))

    class Locator(object):
        from_selfstr = False

        def __init__(self, cls, locator_fn, name=None):
            self.cls = cls
            self.locator_fn = locator_fn
            if name is not None:
                self.name = name

        def __set_name__(self, cls, name):
            setattr(cls, name, type(self)(self.cls, self.locator_fn, name))

        @lazy
        def name(self):
            self.from_selfstr = True
            return self.selfstr()

        def selfstr(self):
            return '%s_%s' % (self.cls.__name__, hex(id(self)))

        def __get__(self, target, cls=None):
            if target is None:
                return self

            name = self.name
            if self.from_selfstr:
                api = getattr(target, name, None)
                if api is not None:
                    return api

            api = self.locator_fn(target)
            cls = self.cls
            if not isinstance(api, cls):
                raise ValueError('API %r is not a %s' % (api, cls.__name__))

            setattr(target, name, api)
            return api

class API(APINoABC, abc.ABC):
    pass

method = abc.abstractmethod
clsmethod = abc.abstractclassmethod
property = abc.abstractproperty
