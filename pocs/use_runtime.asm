.text
	.globl user_code
user_code:
        call RuntimeHello
        pushl $42
        call RuntimeWithParam
        addl $0x4, %esp
        call RuntimeHello
        call RuntimeReturning
        pushl %eax
        call RuntimeWithParam
        addl $0x4, %esp
        call RuntimeHello
