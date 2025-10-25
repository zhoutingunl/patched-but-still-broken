import time
from typing import List, Optional
import requests
import pandas as pd
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS


def timeout_pair(connect_timeout: float = 5000.0, read_timeout: float = 30000.0) -> tuple:
    return (connect_timeout, read_timeout)


def _to_ascii_or_raise(name: str, val: str) -> str:
    if val is None:
        raise ValueError(f"{name} is None")
    cleaned = val.strip().replace("\u3000", " ")
    try:
        cleaned.encode("latin-1")
    except UnicodeEncodeError as e:
        raise ValueError(f"{name} contains non-ASCII/Latin-1 characters: {repr(cleaned)}") from e
    return cleaned


class InfluxV2Helper:
    def __init__(self, url: str, org: str, token: str, bucket: str, rp: Optional[str] = None,
                 connect_timeout: float = 5000.0, read_timeout: float = 30000.0):
        self.url = url.rstrip("/")
        self.org = _to_ascii_or_raise("org", org)
        self.bucket = _to_ascii_or_raise("bucket", bucket)
        self.rp = rp.strip() if isinstance(rp, str) else rp
        if isinstance(self.rp, str):
            _ = _to_ascii_or_raise("rp", self.rp)

        if not token or token.strip() == "" or token.startswith("替换为"):
            raise ValueError("TOKEN 未设置或仍为占位符，请替换为你的真实 InfluxDB token")
        self.token = token.strip()

        self.connect_timeout = float(connect_timeout)
        self.read_timeout = float(read_timeout)
        self.timeout_tuple = timeout_pair(self.connect_timeout, self.read_timeout)

        self.client = InfluxDBClient(
            url=self.url,
            token=self.token,
            org=self.org,
            timeout=self.timeout_tuple
        )

        self.session = requests.Session()
        self.session.headers.update({"Authorization": f"Token {self.token}"})
        self.requests_timeout = (self.connect_timeout, self.read_timeout)

    def write_points(self, points: List[Point]):
        with self.client.write_api(write_options=SYNCHRONOUS) as write_api:
            write_api.write(bucket=self.bucket, org=self.org, record=points)

    def write_line_protocol(self, lines: List[str]):
        payload = "\n".join(lines)
        with self.client.write_api(write_options=SYNCHRONOUS) as write_api:
            write_api.write(bucket=self.bucket, org=self.org, record=payload)

    def write_dataframe(self, df: pd.DataFrame, measurement: str, tag_columns: Optional[List[str]] = None,
                        field_columns: Optional[List[str]] = None, timestamp_column: Optional[str] = None,
                        timestamp_unit: str = "ns"):
        tag_columns = tag_columns or []
        df_to_write = df.copy()

        if timestamp_column:
            ts = pd.to_datetime(df_to_write[timestamp_column], utc=True, errors="coerce")
            df_to_write.set_index(ts, inplace=True)
            if timestamp_column in df_to_write.columns:
                df_to_write.drop(columns=[timestamp_column], inplace=True)
        elif not isinstance(df_to_write.index, pd.DatetimeIndex):
            df_to_write.index = pd.to_datetime(time.time(), unit="s", utc=True)

        if field_columns is None:
            field_columns = [c for c in df_to_write.columns if c not in tag_columns]

        with self.client.write_api(write_options=SYNCHRONOUS) as write_api:
            write_api.write(
                bucket=self.bucket,
                org=self.org,
                record=df_to_write[field_columns + tag_columns],
                data_frame_measurement_name=measurement,
                data_frame_tag_columns=tag_columns,
                data_frame_timestamp_unit=timestamp_unit,
            )

    def query_influxql(self, ql: str, database: Optional[str] = None, rp: Optional[str] = None) -> pd.DataFrame:
        url = self.url + "/query"
        params = {"db": database or self.bucket, "q": ql}
        if rp or self.rp:
            params["rp"] = rp or self.rp

        r = self.session.get(url, params=params, timeout=self.requests_timeout)
        r.raise_for_status()
        payload = r.json()
        results = payload.get("results", [])
        if not results:
            return pd.DataFrame()
        result = results[0]
        if "series" not in result:
            return pd.DataFrame()

        frames = []
        for serie in result["series"]:
            cols = serie.get("columns", [])
            values = serie.get("values", [])
            tags = serie.get("tags", {})
            df = pd.DataFrame(values, columns=cols)
            for k, v in (tags or {}).items():
                df[k] = v
            frames.append(df)
        return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

    def query_flux(self, flux: str) -> pd.DataFrame:
        dfs = self.client.query_api().query_data_frame(query=flux, org=self.org)
        if isinstance(dfs, list):
            return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()
        return dfs
