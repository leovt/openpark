import logging, logging.config

conf = {'formatters': {'simple': {'format': '%(asctime)s - %(name)s - '
                                            '%(levelname)s - %(message)s'}},
        'handlers': {'console': {'class': 'logging.StreamHandler',
                                 'formatter': 'simple',
                                 'level': 'DEBUG'},
                     },
        'loggers': {'': {'handlers': ['console'], 'level': 'DEBUG'}},
        'version': 1}

import pprint
pprint.pprint(conf)

logger = logging.getLogger('child')
print(logger.disabled)

logging.config.dictConfig(conf)
print(logger.disabled)

logger2 = logging.getLogger('child2')
print(logger2.disabled)

print(logging.getLogger().level)

logging.debug('debug message from root')
logging.error('error message from root')
logger.debug('debug message from child')
logger.error('error message from child')

print(logger.getEffectiveLevel())
