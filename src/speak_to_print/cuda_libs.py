"""pip ile gelen CUDA kütüphanelerini, model yüklenmeden önce belleğe alır.

Neden gerekli?
    ctranslate2 (faster-whisper'ın motoru), cuBLAS'ı ilk GPU işleminde
    `libcublas.so.12` adıyla açıyor (dlopen). Bu kütüphane sistemde değil,
    .venv içindeki `nvidia-cublas-cu12` paketinde duruyor ve Linux'un
    kütüphane yükleyicisi orayı aramıyor. Normalde bunun için program
    başlamadan önce LD_LIBRARY_PATH ayarlamak gerekir. Bu, Kickoff'tan
    açılışta zahmetli.

    Onun yerine kütüphaneleri tam yollarıyla ve RTLD_GLOBAL ile önceden
    yüklüyoruz. Aynı adlı (soname) bir kütüphane zaten yüklüyse, sonradan
    gelen `dlopen("libcublas.so.12")` çağrısı onu yeniden kullanır.

    Java karşılığı: `System.load("/tam/yol/libfoo.so")` ile
    `java.library.path` ayarlamadan yerel kütüphane yüklemek gibi.
"""

from __future__ import annotations

import ctypes
import importlib.util
from pathlib import Path

# (Python paketi, sırayla yüklenecek kütüphaneler). libcublas, libcublasLt'ye
# bağlı olduğu için önce o yüklenir.
_CUDA_LIBRARIES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("nvidia.cublas", ("libcublasLt.so.12", "libcublas.so.12")),
)


def _package_lib_dir(package: str) -> Path | None:
    spec = importlib.util.find_spec(package)
    if spec is None or not spec.submodule_search_locations:
        return None
    return Path(next(iter(spec.submodule_search_locations))) / "lib"


def preload_cuda_libraries() -> list[Path]:
    """CUDA kütüphanelerini yükler ve yüklenenlerin yollarını döndürür.

    Paket kurulu değilse sessizce atlar; o durumda GPU kullanılamaz ve
    model yüklenirken ctranslate2 anlaşılır bir hata verir.
    """
    loaded: list[Path] = []
    for package, names in _CUDA_LIBRARIES:
        lib_dir = _package_lib_dir(package)
        if lib_dir is None:
            continue
        for name in names:
            path = lib_dir / name
            if path.exists():
                ctypes.CDLL(str(path), mode=ctypes.RTLD_GLOBAL)
                loaded.append(path)
    return loaded
