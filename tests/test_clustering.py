"""Task 1 verification: a valid location finds parcels, central Lisbon raises EmptyClusterError."""

import pytest

from agri_dss.clustering import EmptyClusterError, find_cluster
from agri_dss.data_loader import load_parcels, url_downloader
from dss_pipeline import DATA_URL


@pytest.fixture(scope="module")
def parcels():
    """Download (if needed) and load the parcels once for all tests in this file."""
    return load_parcels(url_downloader(DATA_URL))


def test_valid_location_finds_parcels(parcels):
    # The PDF's Alentejo example (38.015, -7.865) has no parcels within 150 m in PT.zip
    # (nearest is ~1.3 km away), so we use a point inside a wheat parcel 1.3 km west
    cluster = find_cluster(parcels, 38.0157, -7.8809)
    assert len(cluster) > 0


def test_lisbon_raises_empty_cluster_error(parcels):
    with pytest.raises(EmptyClusterError):
        find_cluster(parcels, 38.722, -9.139)
