
# StoryCLI

StoryCLI is an unofficial CLI tool for downloading your favourite audiobooks
from Storytel without leaving your terminal. An active Storytel account is 
required for using this tool.

I am not responsible for any issues that this tool could cause, including
but not limited to account blocking, temporary or permanent bans, loss of 
time or monet. I built this tool only as a learning experience, and making
it open-source so other people can see the source code and learn. Use it 
at your own risk.

- Download from PyPI: `pipx install storycli`

## Authentication

Create `~/.storycli` and fill it with your login credentials:

```
STORYCLI_MAIL=<your-storytel-email>
STORYCLI_PASS=<your-storytel-password>
```

## Usage

```
usage: storycli [-h] (-q QUERY | -D BOOK_ID) [-o PATH] [-H]

Search and download Storytel audiobooks.

options:
  -h, --help            show this help message and exit
  -q QUERY, --query QUERY
                        search for audiobooks
  -D BOOK_ID, --download BOOK_ID
                        download an audiobook
  -o PATH, --output PATH
                        MP3 output path (required with --download)
  -H, --human-readable  do not format query lengths as hours:minutes:seconds

```

**Search an Audiobook:**

    storycli -q <search-query>
    storycli -q Dune
    storycli --query Dune

    ID       LENGTH    TITLE 
    -------  --------  ---------------
    ...
    2759046   18:36:1  Paul of Dune
    2836812  17:19:18  The Winds of Dune
    2835170  19:31:19  Sandworms of Dune
    ...

**Download an Audiobook:**

    storycli -D <book-id> -o <mp3-save-path>
    storycli -D 2759046 -o ~/Downloads/2759046.mp3
    storycli --download 2759046 -o ~/Downloads/2759046.mp3

## Development

* Install the `uv` project manager.
* Clone the project and run `uv sync`.

## Future Improvements

* Prevent logging in everytime by storing login tokens.
* Add book description preview.
* Better UX.
* Standalone Storytel TUI with builtin player.
* Better error message management.

## License 

MIT