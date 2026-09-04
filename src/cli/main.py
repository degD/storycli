"""StoryCLI: CLI tool to download audiobooks from Storytel."""

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding
from pathlib import Path
from tqdm import tqdm
import argparse
import dotenv
import os
import requests
import sys


class LoginInfo:
    KEY = b"VQZBJ6TD8M9WBUWT"
    IV = b"joiwef08u23j341a"

    def __init__(self, email: str, password: str):
        self.email = email
        self.password = self.__hashPassword(password)

    def __hashPassword(self, password: str) -> str:
        padder = padding.PKCS7(algorithms.AES.block_size).padder()  # type: ignore
        padded_password = padder.update(password.encode("utf-8"))
        padded_password += padder.finalize()
        cipher = Cipher(algorithms.AES(LoginInfo.KEY), modes.CBC(LoginInfo.IV))
        encryptor = cipher.encryptor()
        ciphertext = encryptor.update(padded_password)
        ciphertext += encryptor.finalize()
        return ciphertext.hex().upper()


class AccountInfo:
    def __init__(self, jwt: str, sst: str):
        self.jwt = jwt
        self.sst = sst


class BookData:
    def __init__(self, id: int, title: str, authors: str, length: int, description: str):
        self.id = id
        self.title = title
        self.authors = authors
        self.length = length
        self.description = description


class StoryAPI:
    CHUNK_SIZE = 1048576  # 1 MB

    def __init__(self):
        self.accountInfo: AccountInfo | None = None

    def login(self, loginInfo: LoginInfo) -> bool:
        url = f"https://www.storytel.com/api/login.action?m=1&uid={loginInfo.email.strip()}&pwd={loginInfo.password}"
        try:
            response = requests.get(url)
            if response.status_code == 200:
                data = response.json()
                self.accountInfo = AccountInfo(
                    data["accountInfo"]["jwt"],
                    data["accountInfo"]["singleSignToken"],
                )
                return True
        except (requests.RequestException, KeyError, ValueError):
            pass
        return False

    def searchBook(self, query: str) -> tuple[bool, list[BookData]]:
        if self.accountInfo is None:
            return (False, [])
        try:
            url = f"https://www.storytel.com/api/search.action?q={query}&token={self.accountInfo.sst}"
            response = requests.get(url)
            if response.status_code != 200:
                return (False, [])
            books = [book for book in response.json()["books"] if book["abook"] is not None]
            return (True, [
                BookData(
                    book["abook"]["id"],
                    book["book"]["name"],
                    book["book"]["authorsAsString"],
                    book["abook"]["length"],
                    book["abook"]["description"],
                )
                for book in books
            ])
        except (requests.RequestException, KeyError, TypeError, ValueError):
            return (False, [])

    def downloadBook(self, bookId: int, path: Path) -> bool:
        if self.accountInfo is None:
            return False
        url = f"https://www.storytel.com/mp3streamRangeReq?startposition=0&programId={bookId}&token={self.accountInfo.sst}"
        try:
            response = requests.get(url, stream=True)
            if response.status_code == 200:
                with open(path, "wb") as file:
                    total_size = int(response.headers.get("content-length", 0)) or None
                    with tqdm(total=total_size, unit="B", unit_scale=True, desc="Downloading") as progress:
                        for chunk in response.iter_content(chunk_size=self.CHUNK_SIZE):
                            if chunk:
                                file.write(chunk)
                                progress.update(len(chunk))
                return True
        except (OSError, TypeError, ValueError, requests.RequestException):
            pass
        return False


class StoryCLI:
    LOGIN_FILE_PATH = Path("~/.storycli")

    def __init__(self):
        self.api = StoryAPI()
        login_info = self.__loadLoginInfo()
        if login_info is None:
            self.status = 1
        elif not self.api.login(login_info):
            self.status = 2
        else:
            self.status = 0

    def __loadLoginInfo(self) -> LoginInfo | None:
        dotenv.load_dotenv(self.LOGIN_FILE_PATH.expanduser())
        email = os.getenv("STORYCLI_MAIL")
        password = os.getenv("STORYCLI_PASS")
        if email is not None and password is not None:
            return LoginInfo(email, password)
        return None

    def search(self, query: str) -> tuple[bool, list[BookData]]:
        return self.api.searchBook(query) if self.status == 0 else (False, [])

    def description(self, bookId: int) -> tuple[bool, str | None]:
        success, books = self.search(str(bookId))
        for book in books:
            if book.id == bookId:
                return (True, book.description)
        return (success, None)

    def download(self, bookId: int, path: Path) -> bool:
        return self.status == 0 and self.api.downloadBook(bookId, path)


def format_length(length: int) -> str:
    seconds = length // 1000
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    return f"{hours}:{minutes}:{seconds % 60}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Search and download Storytel audiobooks.")
    operations = parser.add_mutually_exclusive_group(required=True)
    operations.add_argument("-q", "--query", metavar="QUERY", help="search for audiobooks")
    operations.add_argument("-d", "--desc", type=int, metavar="BOOK_ID", help="show a book description")
    operations.add_argument("-D", "--download", type=int, metavar="BOOK_ID", help="download an audiobook")
    parser.add_argument("-o", "--output", type=Path, metavar="PATH", help="MP3 output path (required with --download)")
    parser.add_argument("-H", "--human-readable", action="store_true", help="format query lengths as hours:minutes:seconds")
    args = parser.parse_args(argv)

    if args.download is not None and args.output is None:
        parser.error("--output is required with --download")
    if args.download is None and args.output is not None:
        parser.error("--output may only be used with --download")

    cli = StoryCLI()
    if cli.status == 1:
        print("error: credentials missing; set STORYCLI_MAIL and STORYCLI_PASS in ~/.storycli", file=sys.stderr)
        return 1
    if cli.status == 2:
        print("error: login failed; check the credentials in ~/.storycli", file=sys.stderr)
        return 2

    if args.query is not None:
        success, books = cli.search(args.query)
        if not success:
            print("error: search failed", file=sys.stderr)
            return 3
        for book in books:
            length = format_length(book.length) if args.human_readable else str(book.length)
            print(f"{str(book.id).rjust(10)}  {length.rjust(8)}  {book.title}")
        return 0

    if args.desc is not None:
        success, description = cli.description(args.desc)
        if not success:
            print("error: description lookup failed", file=sys.stderr)
            return 3
        if description is None:
            print(f"error: book {args.desc} was not found", file=sys.stderr)
            return 4
        print(description)
        return 0

    if cli.download(args.download, args.output):
        return 0
    print(f"error: download failed for book {args.download}", file=sys.stderr)
    return 3
