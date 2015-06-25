from glad.lang.c.generator import CGenerator


DEFAULT_DEBUG_IMPL = '''
    {return_def}
    _pre_call_callback("{name}", {args_callback});
    {return_assign} glad_{name}({args});
    _post_call_callback("{name}", {args_callback});
    {return_return}
'''


DEBUG_HEADER = '''
#define GLAD_DEBUG
typedef void (* GLADcallback)(const char *name, void *funcptr, int len_args, ...);

GLAPI void glad_set_pre_callback(GLADcallback cb);
GLAPI void glad_set_post_callback(GLADcallback cb);
'''

DEBUG_CODE = '''
void _pre_call_callback_default(const char *name, void *funcptr, int len_args, ...) {}

static GLADcallback _pre_call_callback = _pre_call_callback_default;
void glad_set_pre_callback(GLADcallback cb) {
    _pre_call_callback = cb;
}

void _post_call_callback_default(const char *name, void *funcptr, int len_args, ...) {
    GLenum error_code;
    error_code = glad_glGetError();

    if (error_code != GL_NO_ERROR) {
        fprintf(stderr, "ERROR %d in %s\\n", error_code, name);
    }
}

static GLADcallback _post_call_callback = _post_call_callback_default;
void glad_set_post_callback(GLADcallback cb) {
    _post_call_callback = cb;
}
'''


class CDebugGenerator(CGenerator):
    def write_code_head(self, f):
        CGenerator.write_code_head(self, f)
        self._f_c.write(DEBUG_CODE)

    def write_api_header(self, f):
        CGenerator.write_api_header(self, f)
        f.write(DEBUG_HEADER)

    def write_function_prototype(self, fobj, func):
        fobj.write('typedef {} (APIENTRYP PFN{}PROC)({});\n'.format(
            func.proto.ret.to_c(), func.proto.name.upper(),
            ', '.join(param.type.to_c() for param in func.params)
        ))
        fobj.write('GLAPI PFN{}PROC glad_{};\n'.format(
            func.proto.name.upper(), func.proto.name
        ))
        fobj.write('GLAPI PFN{}PROC glad_debug_{};\n'.format(
            func.proto.name.upper(), func.proto.name
        ))
        fobj.write('#define {0} glad_debug_{0}\n'.format(func.proto.name))

    def write_function(self, fobj, func):
        fobj.write('PFN{}PROC glad_{};\n'.format(
            func.proto.name.upper(), func.proto.name
        ))

        # write the default debug function
        args_def = ', '.join(
            '{type} arg{i}'.format(type=param.type.to_c(), i=i)
            for i, param in enumerate(func.params)
        )
        fobj.write('{} glad_debug_impl_{}({}) {{'.format(
            func.proto.ret.to_c(), func.proto.name, args_def
        ))
        args = ', '.join('arg{}'.format(i) for i, _ in enumerate(func.params))
        args_callback = ', '.join(filter(
            None, ['(void*){}'.format(func.proto.name), str(len(func.params)), args]
        ))
        return_def = ''
        return_assign = ''
        return_return = ''
        if not func.proto.ret.type.lower() == 'void':
            return_def = '\n    {} ret;'.format(func.proto.ret.to_c())
            return_assign = 'ret = '
            return_return = 'return ret;'
        fobj.write('\n'.join(filter(None, DEFAULT_DEBUG_IMPL.format(
            name=func.proto.name, args=args, args_callback=args_callback,
            return_def=return_def, return_assign=return_assign,
            return_return=return_return
        ).splitlines())))
        fobj.write('\n}\n')

        fobj.write('PFN{0}PROC glad_debug_{1} = glad_debug_impl_{1};\n'.format(
            func.proto.name.upper(), func.proto.name
        ))