from dataclasses import dataclass
from threading import RLock
from uuid import uuid4
import pandas as pd
from backend.services.profiler import profile


@dataclass
class Dataset:
    id: str
    name: str
    raw: pd.DataFrame
    frame: pd.DataFrame
    cleaning: dict
    profiling: dict


class DatasetStore:
    def __init__(self):
        self.items: dict[str, Dataset] = {}
        self.lock = RLock()

    def add(self, name, raw, frame, cleaning):
        with self.lock:
            memory = sum(
                d.raw.memory_usage(deep=True).sum()
                + d.frame.memory_usage(deep=True).sum()
                for d in self.items.values()
            )
            memory += (
                raw.memory_usage(deep=True).sum() + frame.memory_usage(deep=True).sum()
            )
            if len(self.items) >= 20 or memory > 1_500_000_000:
                raise ValueError(
                    "메모리 한도(1.5GB / 20개 데이터셋)에 도달했습니다. 불필요한 데이터셋을 삭제해주세요."
                )
            dataset = Dataset(
                str(uuid4()), name.strip(), raw, frame, cleaning, profile(frame)
            )
            self.items[dataset.id] = dataset
            return dataset

    def get(self, identifier):
        with self.lock:
            if identifier not in self.items:
                raise ValueError(
                    "데이터셋을 찾을 수 없습니다. 서버 재시작 시 메모리 데이터는 초기화됩니다."
                )
            return self.items[identifier]

    def frames(self):
        with self.lock:
            return {k: v.frame for k, v in self.items.items()}


store = DatasetStore()
