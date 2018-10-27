POINTER_SIZE = 4
INT_TAG_MULTIPLIER = 2
INT_TAG_SHIFT = 1
PTR_TAG = 1
INT_TAG = 0
INT_PTR_TAG_MASK = 1

FUNCTION_CONTEXT_HEADER_SIZE = 4 * POINTER_SIZE

# The function context contains the outer function context, the spill
# count, and the params & locals count.
FUNCTION_CONTEXT_OUTER_FUNCTION_CONTEXT_OFFSET = 0
FUNCTION_CONTEXT_SPILL_COUNT_OFFSET = 1
FUNCTION_CONTEXT_PARAMS_OFFSET = 4
# FIXME: inconsistent naming

# Function offsets
FUNCTION_OFFSET_FUNCTION_CONTEXT = 0
FUNCTION_OFFSET_ADDRESS = 1
FUNCTION_OFFSET_RETURN_VALUE_OFFSET = 2

# These need to be multiplied by POINTER_SIZE.
SPILL_AREA_FROM_EBP_OFFSET = -3
FUNCTION_CONTEXT_FROM_EBP_OFFSET = -2

MAIN_NAME = "__main"

# Errors
ERROR_ID_ARRAY_INDEX_NOT_INT = 0
