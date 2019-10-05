'''
Lazier

Allows for calculation of class members on demand.  Members can be derived from
methods or other attributes/methods.  Once calculated, lazily computed values
remain with the object until deleted.

Basic Usage:

>>> class MyClass(object):
...     @lazy                 # Optional () without arguments
...     def x(self):
...         print("Creating")
...         return 'x'

>>> obj = MyClass()
>>> obj.x
Creating
'x'
>>> obj.x
'x'

Requiring a resulting type, generic requirements, and type conversion:

>>> class MyClass(object):
...     def __init__(self, x_init):
...         self.x_init = x_init
...
...     @lazy(require=int)
...     def x(self):
...         return self.x_init
...
...     def n_gt_5(n):
...         return n > 5
...
...     @lazy(require=n_gt_5)
...     def x_gt_5(self):
...         return self.x_init
...
...     @lazy(into=int)
...     def x_as_int(self):
...         return self.x_init

>>> obj = MyClass(5)
>>> obj.x
5
>>> obj = MyClass('hello')
>>> obj.x
Traceback (most recent call last):
    ...
TypeError: 'hello' is not a 'int'

>>> MyClass('5').x_as_int
5

>>> MyClass(7).x_gt_5
7

>>> MyClass(3).x_gt_5
Traceback (most recent call last):
    ...
ValueError: 3 did not pass 'n_gt_5'

'''

import sys, abc
#sys.setrecursionlimit(25)

if sys.version_info >= (3, 6):
    def if_python_36_or_newer():
        '''
        The following only work with Python 3.6 or later:    
        
        Specifying a factory method:

        >>> class Base(object):
        ...     @lazy('x')
        ...     def get_x(self):
        ...         return 'x from base_x'

        >>> class Subclass(Base):
        ...     def get_x(self):
        ...         return 'x from sub_x'

        >>> obj = Base()
        >>> obj.x
        'x from base_x'
        >>> obj.x
        'x from base_x'
        
        >>> obj = Subclass()
        >>> obj.x
        'x from sub_x'
        >>> obj.x
        'x from sub_x'
        
        Making it an abstract method:

        >>> class Base(abc.ABC):
        ...     @lazy('x', abstract=True)
        ...     def get_x(self):
        ...         return 'x from base_x'

        >>> class Subclass(Base):
        ...     def get_x(self):
        ...         return 'x from sub_x'
        
        >>> obj = Subclass()
        >>> obj.x
        'x from sub_x'

        '''

class Singleton(str):
    pass
VOLATILE = Singleton('VOLATILE')    

def lazy(fn=None, name=None, method=None, require=None, 
                  abstract=False, into=None):
    if fn is None:
        # If fn wasn't specified this is a zero-argument use, lazy(). so the 
        # function will be passed to the builder function.
        def builder(fn):
            return lazy(fn, name=name, method=method, 
                            require=require, abstract=abstract, into=into)
        return builder

    elif isinstance(fn, str):
        # If fn is a string, it's really specifying the property name.  Again,
        # a function will be passed to the builder, but we'll use the fn 
        # argument as the name.
        def builder(fn, name=fn):
            return lazy(fn, name=name, method=method, 
                            require=require, abstract=abstract, into=into)
        return builder

    elif callable(fn):
        # Only callable types may pass.

        if name is None:
            # If name was not passed, use the function name.
            name = fn.__name__
        elif name != fn.__name__:
            # If passed but not the same as the function, bias method to True
            if method is None:
                method = True

        if method:            
            # If method is not false, it's either simply True or the name of
            # the method to invoke when retrieving the value.
            def src(obj, cls=None, name=fn.__name__ if method is True else method):
                return getattr(obj, name)()
        else:
            # Method is falsy, so the source is the fn passed.
            src = fn
            
        if isinstance(require, type):
            prepare = type_checker(require)
        elif require is not None:
            prepare = requirement_checker(require)
        else:
            prepare = None
            
        if into is not None:
            if prepare is None:
                prepare = into
            else:                
                prepare = lambda o: into(prepare(o))

        # Now for the actual get function for the property.
        def getter(self, obj, cls=None, name=name, VOLATILE=VOLATILE, 
                         src=src, prepare=prepare):
            if cls is None:
                # Without a second argument, obj is the class.  This usually means
                # that we are being probed by pydoc or other introspection.
                return self
            else:
                # Otherwise, get the result.  If it is not VOLATILE, store it
                # in the object's __dict__, which will then be offered when the
                # attribute is accessed.
                result = src(obj)
                if prepare is not None:
                    result = prepare(result)
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
            # requires Python3.6 to support the __set_name__ magic method.
            if abstract:
                fn = abc.abstractmethod(fn)
            def configure_class_for_lazy(self, cls, fn_name, name=name):
                setattr(cls, name, type(name, (), clsdict)())
                setattr(cls, fn.__name__, fn)
            clsdict['__set_name__'] = configure_class_for_lazy
            return type(name, (), clsdict)()

    else:
        # The fn isn't a valid type.  Bomb out.
        raise TypeError('Attempt to use %r as a lazy function' % fn)

def type_checker(isa):
    def type_checker(obj, isa=isa):
        if not isinstance(obj, isa):
            raise TypeError('%r is not a %r' % (obj, isa.__name__))
        else:
            return obj
    return type_checker            

def requirement_checker(requirement):
    def requirement_checker(obj, requirement=requirement):
        if requirement(obj) is False:
            raise ValueError('%r did not pass %r' % (obj, requirement.__name__))
        else:
            return obj
    return requirement_checker            
