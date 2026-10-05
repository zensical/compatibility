# Copyright (c) 2026 Zensical and contributors

# SPDX-License-Identifier: MIT
# All contributions are certified under the DCO

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to
# deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
# sell copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NON-INFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.

def define_env(env):
    env.variables.registered = env.variables.shared + '/' + env.variables.included
    env.variables.shared = 'module'
    env.variables.nested.value = 'changed'
    env.variables.shadowed = 'variable'
    env.variables.plugin = 'module plugin'
    env.macro(lambda: 'macro', 'shadowed')
    env.macro(lambda: 'module', 'custom_macro')
    env.macro(lambda: 'custom context', 'context')
    env.macro(lambda: 'custom now', 'now')
    env.macro(lambda: 'custom diagnostics', 'macros_info')
    env.filter(lambda value: value.upper(), 'shout')
