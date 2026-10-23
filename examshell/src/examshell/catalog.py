"""Exercise definitions and private grading cases."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Exercise:
    slug: str
    level: int
    source: str
    description: str
    function_harness: str | None = None
    function_expected: str | None = None
    cases: tuple[tuple[tuple[str, ...], str], ...] = ()


EXERCISES = (
    Exercise(
        slug="ft_strlen",
        level=1,
        source="ft_strlen.c",
        description="Implemente ft_strlen para retornar o número de caracteres da string, sem contar o byte nulo final.",
        function_harness=(
            '#include <stdio.h>\n'
            'int ft_strlen(char *str);\n'
            'int main(void) { printf("%d\\n%d\\n", ft_strlen(""), ft_strlen("42 school")); return 0; }\n'
        ),
        function_expected="0\n9\n",
    ),
    Exercise(
        slug="ft_swap",
        level=1,
        source="ft_swap.c",
        description="Implemente ft_swap para trocar os valores apontados pelos dois ponteiros recebidos.",
        function_harness=(
            '#include <stdio.h>\n'
            'void ft_swap(int *a, int *b);\n'
            'int main(void) { int a = -3, b = 42; ft_swap(&a, &b); printf("%d %d\\n", a, b); return 0; }\n'
        ),
        function_expected="42 -3\n",
    ),
    Exercise(
        slug="first_word",
        level=1,
        source="first_word.c",
        description="Escreva um programa que imprima a primeira palavra do argumento, ignorando espaços e tabulações antes dela.",
        cases=(
            (("  hello   world",), "hello"),
            (("\t42 school",), "42"),
            (("   ",), ""),
        ),
    ),
    Exercise(
        slug="last_word",
        level=2,
        source="last_word.c",
        description="Escreva um programa que imprima a última palavra do argumento, ignorando espaços e tabulações ao redor.",
        cases=(
            (("hello   world  ",), "world"),
            (("one",), "one"),
            ((" \t ",), ""),
        ),
    ),
    Exercise(
        slug="wdmatch",
        level=2,
        source="wdmatch.c",
        description="Imprima a primeira string apenas quando todos os seus caracteres aparecem, na mesma ordem, na segunda string.",
        cases=(
            (("faya", "f this is a test y a"), "faya"),
            (("abc", "acb"), ""),
            (("42", "4--2"), "42"),
        ),
    ),
)

# Exercises used by the app's personalized path. They are intentionally kept
# outside EXERCISES so the standalone trial/normal banks remain five questions.
API_EXERCISES = (
    Exercise(
        slug="ft_strdup",
        level=2,
        source="ft_strdup.c",
        description="Implemente ft_strdup: aloque memória para uma cópia de src, copie a string e retorne o novo endereço.",
        function_harness=(
            '#include <stdio.h>\n'
            '#include <stdlib.h>\n'
            'char *ft_strdup(char *src);\n'
            'int main(void) { char *a = ft_strdup(""); char *b = ft_strdup("42 School"); '
            'if (!a || !b) return 2; printf("%s\\n%s\\n", a, b); free(a); free(b); return 0; }\n'
        ),
        function_expected="\n42 School\n",
    ),
    Exercise(
        slug="ft_range",
        level=2,
        source="ft_range.c",
        description="Implemente ft_range para alocar e retornar um vetor com os inteiros de start (inclusivo) até end (exclusivo). Retorne NULL quando start for maior ou igual a end.",
        function_harness=(
            '#include <stdio.h>\n'
            '#include <stdlib.h>\n'
            'int *ft_range(int start, int end);\n'
            'int main(void) { int *a = ft_range(-2, 3); int *b = ft_range(4, 4); '
            'if (!a) return 2; for (int i = 0; i < 5; i++) printf("%d%c", a[i], i == 4 ? \'\\n\' : \' \'); '
            'printf("%s\\n", b ? "not-null" : "null"); free(a); free(b); return 0; }\n'
        ),
        function_expected="-2 -1 0 1 2\nnull\n",
    ),
)


def by_slug(slug: str) -> Exercise:
    for exercise in (*EXERCISES, *API_EXERCISES):
        if exercise.slug == slug:
            return exercise
    raise KeyError(slug)
