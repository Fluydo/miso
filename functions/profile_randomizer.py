"""
functions/profile_randomizer.py
Random profile generator for bot profiles.
"""

import json
import logging
import random
from pathlib import Path
from typing import Optional, Tuple

import config

logger = logging.getLogger("miso.functions.profile_randomizer")


def get_random_profile() -> Tuple[str, str, str]:
    """
    Get a random profile (name, pfp path, banner path).
    
    Returns:
        Tuple of (display_name, pfp_filename, banner_filename)
    """
    profile_dir = config.BASE_DIR / "profile"
    
    # Load random name
    names_file = profile_dir / "names.json"
    try:
        with open(names_file, 'r', encoding='utf-8') as f:
            names = json.load(f)
        display_name = random.choice(names)
    except Exception as e:
        logger.error(f"Failed to load names.json: {e}")
        display_name = "Miso Bot"
    
    # Get random pfp
    pfps_dir = profile_dir / "pfps"
    try:
        pfp_files = list(pfps_dir.glob("*.*"))
        if pfp_files:
            pfp_file = random.choice(pfp_files)
            pfp_filename = pfp_file.name
        else:
            logger.warning("No pfp files found")
            pfp_filename = None
    except Exception as e:
        logger.error(f"Failed to get random pfp: {e}")
        pfp_filename = None
    
    # Get random banner
    banners_dir = profile_dir / "banners"
    try:
        banner_files = list(banners_dir.glob("*.*"))
        if banner_files:
            banner_file = random.choice(banner_files)
            banner_filename = banner_file.name
        else:
            logger.warning("No banner files found")
            banner_filename = None
    except Exception as e:
        logger.error(f"Failed to get random banner: {e}")
        banner_filename = None
    
    logger.info(f"Generated random profile: name='{display_name}', pfp={pfp_filename}, banner={banner_filename}")
    return display_name, pfp_filename, banner_filename


def get_profile_asset_path(asset_type: str, filename: str) -> Optional[Path]:
    """
    Get the full path to a profile asset.
    
    Args:
        asset_type: Either 'pfps' or 'banners'
        filename: The filename of the asset
    
    Returns:
        Path object or None if not found
    """
    profile_dir = config.BASE_DIR / "profile"
    asset_path = profile_dir / asset_type / filename
    
    if asset_path.exists():
        return asset_path
    else:
        logger.warning(f"Asset not found: {asset_path}")
        return None
