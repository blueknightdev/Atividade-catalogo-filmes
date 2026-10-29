"""Exceções de domínio. Não dependem de nenhum framework."""


class ErroDeDominio(Exception):
    """Base para todos os erros de regra de negócio."""


class DadosInvalidos(ErroDeDominio):
    pass


class NaoEncontrado(ErroDeDominio):
    pass


class JaExiste(ErroDeDominio):
    pass


class NaoAutenticado(ErroDeDominio):
    pass


class NaoAutorizado(ErroDeDominio):
    pass


class IdadeInsuficiente(ErroDeDominio):
    pass
