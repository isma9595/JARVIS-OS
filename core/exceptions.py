class JarvisError(Exception):
    pass


class KernelError(JarvisError):
    pass


class ModuleError(JarvisError):
    pass


class SecurityError(JarvisError):
    pass
