from line_wrapper import LineWrapper

w = LineWrapper(
    "Perguntar se o paciente sente a picada nítida ou amortecimento só gera confusão e má interpretação.",
    limit=50,
    debug=True
)

w.print()