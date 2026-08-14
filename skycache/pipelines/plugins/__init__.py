"""Built-in decoder plugins."""

from skycache.pipelines.plugins.bulk_open_pack import BulkOpenPackPlugin
from skycache.pipelines.plugins.community_board import CommunityBoardPlugin
from skycache.pipelines.plugins.corpus_folder_import import CorpusFolderImportPlugin
from skycache.pipelines.plugins.gr_satellites_wrapper import GrSatellitesPlugin
from skycache.pipelines.plugins.open_data_hint import OpenDataHintPlugin
from skycache.pipelines.plugins.open_fta_sim import OpenFtaSimPlugin
from skycache.pipelines.plugins.open_http_import import OpenHttpImportPlugin
from skycache.pipelines.plugins.package_import import PackageImportPlugin
from skycache.pipelines.plugins.satdump_weather import SatDumpWeatherPlugin
from skycache.pipelines.plugins.sim_file import SimFilePlugin

BUILTIN_PLUGINS = [
    SimFilePlugin(),
    OpenFtaSimPlugin(),
    SatDumpWeatherPlugin(),
    GrSatellitesPlugin(),
    PackageImportPlugin(),
    BulkOpenPackPlugin(),
    OpenDataHintPlugin(),
    CommunityBoardPlugin(),
    OpenHttpImportPlugin(),
    CorpusFolderImportPlugin(),
]

__all__ = [
    "BUILTIN_PLUGINS",
    "SimFilePlugin",
    "OpenFtaSimPlugin",
    "SatDumpWeatherPlugin",
    "GrSatellitesPlugin",
    "PackageImportPlugin",
    "BulkOpenPackPlugin",
    "OpenDataHintPlugin",
    "CommunityBoardPlugin",
    "OpenHttpImportPlugin",
    "CorpusFolderImportPlugin",
]
