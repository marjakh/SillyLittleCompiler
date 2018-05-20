POINTER_SIZE = 4

FUNCTION_CONTEXT_HEADER_SIZE = 4 * POINTER_SIZE

# The function context contains the outer function context, the spill count, the
# param count and the locals count.
FUNCTION_CONTEXT_SPILL_COUNT_OFFSET = 1
FUNCTION_CONTEXT_PARAMS_OFFSET = 4

# These need to be multiplied by POINTER_SIZE.
SPILL_AREA_FROM_EBP_OFFSET = -3
FUNCTION_CONTEXT_FROM_EBP_OFFSET = -2

