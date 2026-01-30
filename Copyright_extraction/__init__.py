# Copyright (c) 2026 IceT5. All rights reserved
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from .prerequisite import check_scancode_available

from .extract import run_extractcode

from .scancode import run_scancode

from .parse_and_duplication import extract_and_duplicate_copyright

from .cleanup import cleanup_extract_dir

__all__ =[
    "check_scancode_available",
    "run_extractcode",
    "run_scancode",
    "extract_and_duplicate_copyright",
    "cleanup_extract_dir",
]
