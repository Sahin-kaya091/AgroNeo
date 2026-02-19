import ee

def initialize_ee():
    """Earth Engine Authorization and Initialization"""
    try:
        ee.Initialize()
    except:
        ee.Authenticate()
        ee.Initialize()

def mask_s2_clouds(image):
    """Sentinel-2 cloud masking"""
    qa = image.select('QA60')
    cloud_bit_mask = 1 << 10
    cirrus_bit_mask = 1 << 11
    mask = qa.bitwiseAnd(cloud_bit_mask).eq(0).And(qa.bitwiseAnd(cirrus_bit_mask).eq(0))
    return image.updateMask(mask)
