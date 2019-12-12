"""Contains transformer configuration information
"""

# The version number of the transformer
TRANSFORMER_VERSION = '2.1'

# The transformer description
TRANSFORMER_DESCRIPTION = 'Thermal IR Temperature (K) GeoTIFF'

# Short name of the transformer
TRANSFORMER_NAME = 'terra.multispectral.flir2tif'

# The sensor associated with the transformer
TRANSFORMER_SENSOR = 'flirIrCamera'

# The transformer type (eg: 'rgbmask', 'plotclipper')
TRANSFORMER_TYPE = 'flir2tif'

# The name of the author of the extractor
AUTHOR_NAME = 'Max Burnette'

# The email of the author of the extractor
AUTHOR_EMAIL = 'mburnet2@illinois.edu'

# Contributors to this transformer
CONTRUBUTORS = ['Zongyang Li', 'Solmaz Hajmohammadi']

# Reposity URI of where the source code lives
REPOSITORY = 'https://github.com/AgPipeline/transformer-flir2tif'
