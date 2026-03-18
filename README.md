# OSSchecktools
Provide some tools for inspection work in the open source software field.

## OSS Information Extraction Tool

A tool for extracting copyright and license information from open source software source packages. This tool automatically extracts copyright and license information from source code archives or directories and generates a standardized `Readme.opensource` file.

### Key Features
- Extract copyright information with automatic deduplication
- Extract license information from open source projects
- Support multiple archive formats: `.zip`, `.tar`, `.tar.gz`, `.tgz`, `.tar.bz2`, `.tbz2`
- Generate standardized `Readme.opensource` file
- Based on [ScanCode Toolkit](https://github.com/nexB/scancode-toolkit)

### Quick Start
```bash
# Enter the tool directory
cd OSSinfo_extraction

# Install the tool
pip install -e .

# Run the tool
cret -t package.zip -n "SoftwareName" -v "1.0.0"
```

### Documentation
For detailed usage, please see [OSSinfo_extraction/README.md](OSSinfo_extraction/README.md).

- [Design Document](OSSinfo_extraction/DESIGN.md) - Detailed design documentation
- [FAQs](OSSinfo_extraction/FAQs.md) - Frequently asked questions

## License
This project is licensed under the Apache License 2.0.