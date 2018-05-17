#ifndef RUNTIME_STACK_WALK_H
#define RUNTIME_STACK_WALK_H

#include <cstdint>
#include <stack>

void stack_walk(std::int32_t* stack_low, std::int32_t* stack_high, std::stack<std::pair<int32_t**, std::int32_t*>>* roots);

#endif
