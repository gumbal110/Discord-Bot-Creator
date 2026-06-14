"""
Michigan RP Welcome Bot
=======================
Bot profesional de bienvenida para la comunidad Michigan RP.
Da la bienvenida automáticamente a nuevos miembros mediante embeds
en el canal configurado y por DM, con soporte completo de comandos slash.
"""

import discord
from discord import app_commands
from discord.ext import commands
import json
import os
import logging
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuración del sistema de logs
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("MichiganRPBot")

# ---------------------------------------------------------------------------
# Ruta al archivo de configuración
# ---------------------------------------------------------------------------
RUTA_CONFIG = Path(__file__).parent / "config.json"


def cargar_config() -> dict:
    """Carga y retorna el archivo config.json como diccionario."""
    with open(RUTA_CONFIG, "r", encoding="utf-8") as archivo:
        return json.load(archivo)


def guardar_config(config: dict) -> None:
    """Guarda el diccionario de configuración en config.json."""
    with open(RUTA_CONFIG, "w", encoding="utf-8") as archivo:
        json.dump(config, archivo, indent=2, ensure_ascii=False)


def reemplazar_variables(texto: str, miembro: discord.Member) -> str:
    """
    Reemplaza las variables de texto con datos reales del miembro.

    Variables disponibles:
      {user}          — usuario completo, ej: "MiUsuario#1234"
      {username}      — nombre de display, ej: "MiUsuario"
      {member_count}  — cantidad total de miembros del servidor
      {server}        — nombre del servidor
      {mention}       — mención @usuario
    """
    return (
        texto.replace("{user}", str(miembro))
             .replace("{username}", miembro.display_name)
             .replace("{member_count}", str(miembro.guild.member_count))
             .replace("{server}", miembro.guild.name)
             .replace("{mention}", miembro.mention)
    )


def construir_embed(config_embed: dict, miembro: discord.Member) -> discord.Embed:
    """
    Construye un discord.Embed a partir de un bloque de configuración.

    Claves soportadas (todas opcionales):
      titulo, descripcion, color (hex como "#FF0000"),
      url_miniatura, url_imagen,
      texto_pie, url_icono_pie,
      nombre_autor, url_icono_autor, url_autor
    """
    # --- Color -----------------------------------------------------------
    color_raw = config_embed.get("color", "#2b2d31")
    try:
        color = discord.Color(int(color_raw.lstrip("#"), 16))
    except (ValueError, AttributeError):
        color = discord.Color.blurple()

    # --- Campos principales ----------------------------------------------
    titulo = reemplazar_variables(config_embed.get("titulo", ""), miembro)
    descripcion = reemplazar_variables(config_embed.get("descripcion", ""), miembro)

    embed = discord.Embed(
        title=titulo or None,
        description=descripcion or None,
        color=color,
        timestamp=datetime.now(timezone.utc),
    )

    # --- Autor -----------------------------------------------------------
    nombre_autor = reemplazar_variables(config_embed.get("nombre_autor", ""), miembro)
    if nombre_autor:
        embed.set_author(
            name=nombre_autor,
            icon_url=config_embed.get("url_icono_autor") or None,
            url=config_embed.get("url_autor") or None,
        )

    # --- Miniatura -------------------------------------------------------
    miniatura = config_embed.get("url_miniatura", "")
    if miniatura:
        embed.set_thumbnail(url=miniatura)

    # --- Imagen / Banner grande ------------------------------------------
    imagen = config_embed.get("url_imagen", "")
    if imagen:
        embed.set_image(url=imagen)

    # --- Pie de página ---------------------------------------------------
    texto_pie = reemplazar_variables(config_embed.get("texto_pie", ""), miembro)
    if texto_pie:
        embed.set_footer(
            text=texto_pie,
            icon_url=config_embed.get("url_icono_pie") or None,
        )

    # --- Campos dinámicos automáticos ------------------------------------
    embed.add_field(name="👤 Usuario", value=miembro.mention, inline=True)
    embed.add_field(
        name="📅 Se unió",
        value=f"<t:{int(miembro.joined_at.timestamp())}:R>" if miembro.joined_at else "Ahora mismo",
        inline=True,
    )
    embed.add_field(
        name="👥 Miembro",
        value=f"#{miembro.guild.member_count}",
        inline=True,
    )

    return embed


# ---------------------------------------------------------------------------
# Modales para editar los embeds desde Discord
# ---------------------------------------------------------------------------

class ModalEditarBienvenida(discord.ui.Modal, title="✏️ Editar Mensaje de Bienvenida"):
    """Formulario para editar el embed del canal de bienvenida."""

    titulo_embed = discord.ui.TextInput(
        label="Título",
        placeholder="¡Bienvenido a {server}, {username}!",
        required=False,
        max_length=256,
    )
    descripcion_embed = discord.ui.TextInput(
        label="Descripción",
        placeholder="Hola {mention}, eres el miembro #{member_count}...",
        required=False,
        style=discord.TextStyle.paragraph,
        max_length=2000,
    )
    color_embed = discord.ui.TextInput(
        label="Color (hex)",
        placeholder="#E8A400",
        required=False,
        max_length=7,
    )
    texto_pie_embed = discord.ui.TextInput(
        label="Texto del pie de página",
        placeholder="Michigan RP • {server}",
        required=False,
        max_length=200,
    )
    nombre_autor_embed = discord.ui.TextInput(
        label="Nombre del autor",
        placeholder="Michigan RP Community",
        required=False,
        max_length=256,
    )

    def __init__(self, config_actual: dict):
        super().__init__()
        embed = config_actual.get("welcome_embed", {})
        # Pre-rellenar los campos con los valores actuales
        self.titulo_embed.default = embed.get("titulo", "")
        self.descripcion_embed.default = embed.get("descripcion", "")
        self.color_embed.default = embed.get("color", "#E8A400")
        self.texto_pie_embed.default = embed.get("texto_pie", "")
        self.nombre_autor_embed.default = embed.get("nombre_autor", "")
        self._config = config_actual

    async def on_submit(self, interaction: discord.Interaction):
        embed_cfg = self._config.setdefault("welcome_embed", {})

        if self.titulo_embed.value:
            embed_cfg["titulo"] = self.titulo_embed.value
        if self.descripcion_embed.value:
            embed_cfg["descripcion"] = self.descripcion_embed.value
        if self.color_embed.value:
            embed_cfg["color"] = self.color_embed.value
        if self.texto_pie_embed.value:
            embed_cfg["texto_pie"] = self.texto_pie_embed.value
        if self.nombre_autor_embed.value:
            embed_cfg["nombre_autor"] = self.nombre_autor_embed.value

        guardar_config(self._config)
        interaction.client.config = self._config

        await interaction.response.send_message(
            "✅ **Mensaje de bienvenida actualizado.** Usa `/testbienvenida` para previsualizarlo.",
            ephemeral=True,
        )
        log.info("Embed de bienvenida editado por %s", interaction.user)


class ModalEditarDM(discord.ui.Modal, title="✏️ Editar Mensaje de DM"):
    """Formulario para editar el embed que se envía por DM al nuevo miembro."""

    titulo_embed = discord.ui.TextInput(
        label="Título",
        placeholder="¡Bienvenido a Michigan RP, {username}!",
        required=False,
        max_length=256,
    )
    descripcion_embed = discord.ui.TextInput(
        label="Descripción",
        placeholder="Hola {mention}, bienvenido a {server}...",
        required=False,
        style=discord.TextStyle.paragraph,
        max_length=2000,
    )
    color_embed = discord.ui.TextInput(
        label="Color (hex)",
        placeholder="#E8A400",
        required=False,
        max_length=7,
    )
    texto_pie_embed = discord.ui.TextInput(
        label="Texto del pie de página",
        placeholder="Michigan RP • ¡Nos alegra tenerte aquí!",
        required=False,
        max_length=200,
    )
    nombre_autor_embed = discord.ui.TextInput(
        label="Nombre del autor",
        placeholder="Equipo de Staff de Michigan RP",
        required=False,
        max_length=256,
    )

    def __init__(self, config_actual: dict):
        super().__init__()
        embed = config_actual.get("dm_embed", {})
        # Pre-rellenar los campos con los valores actuales
        self.titulo_embed.default = embed.get("titulo", "")
        self.descripcion_embed.default = embed.get("descripcion", "")
        self.color_embed.default = embed.get("color", "#E8A400")
        self.texto_pie_embed.default = embed.get("texto_pie", "")
        self.nombre_autor_embed.default = embed.get("nombre_autor", "")
        self._config = config_actual

    async def on_submit(self, interaction: discord.Interaction):
        embed_cfg = self._config.setdefault("dm_embed", {})

        if self.titulo_embed.value:
            embed_cfg["titulo"] = self.titulo_embed.value
        if self.descripcion_embed.value:
            embed_cfg["descripcion"] = self.descripcion_embed.value
        if self.color_embed.value:
            embed_cfg["color"] = self.color_embed.value
        if self.texto_pie_embed.value:
            embed_cfg["texto_pie"] = self.texto_pie_embed.value
        if self.nombre_autor_embed.value:
            embed_cfg["nombre_autor"] = self.nombre_autor_embed.value

        guardar_config(self._config)
        interaction.client.config = self._config

        await interaction.response.send_message(
            "✅ **Mensaje de DM actualizado.** Usa `/testdm` para previsualizarlo.",
            ephemeral=True,
        )
        log.info("Embed de DM editado por %s", interaction.user)


class ModalImagenesBienvenida(discord.ui.Modal, title="🖼️ Imágenes — Canal de Bienvenida"):
    """Formulario para editar las URLs de imágenes del embed de bienvenida."""

    url_miniatura = discord.ui.TextInput(
        label="Miniatura (esquina superior derecha)",
        placeholder="https://i.imgur.com/tu-icono.png",
        required=False,
        max_length=500,
    )
    url_imagen = discord.ui.TextInput(
        label="Banner grande (parte inferior del embed)",
        placeholder="https://i.imgur.com/tu-banner.png",
        required=False,
        max_length=500,
    )
    url_icono_autor = discord.ui.TextInput(
        label="Ícono del autor (junto al nombre del autor)",
        placeholder="https://i.imgur.com/tu-icono.png",
        required=False,
        max_length=500,
    )
    url_icono_pie = discord.ui.TextInput(
        label="Ícono del pie de página",
        placeholder="https://i.imgur.com/tu-icono.png",
        required=False,
        max_length=500,
    )

    def __init__(self, config_actual: dict):
        super().__init__()
        embed = config_actual.get("welcome_embed", {})
        self.url_miniatura.default = embed.get("url_miniatura", "")
        self.url_imagen.default = embed.get("url_imagen", "")
        self.url_icono_autor.default = embed.get("url_icono_autor", "")
        self.url_icono_pie.default = embed.get("url_icono_pie", "")
        self._config = config_actual

    async def on_submit(self, interaction: discord.Interaction):
        embed_cfg = self._config.setdefault("welcome_embed", {})

        # Guardar solo si el campo tiene valor; si se deja vacío se borra
        embed_cfg["url_miniatura"] = self.url_miniatura.value
        embed_cfg["url_imagen"] = self.url_imagen.value
        embed_cfg["url_icono_autor"] = self.url_icono_autor.value
        embed_cfg["url_icono_pie"] = self.url_icono_pie.value

        guardar_config(self._config)
        interaction.client.config = self._config

        await interaction.response.send_message(
            "✅ **Imágenes de bienvenida actualizadas.** Usa `/testbienvenida` para previsualizarlas.",
            ephemeral=True,
        )
        log.info("Imágenes del embed de bienvenida editadas por %s", interaction.user)


class ModalImagenesDM(discord.ui.Modal, title="🖼️ Imágenes — DM de Bienvenida"):
    """Formulario para editar las URLs de imágenes del embed de DM."""

    url_miniatura = discord.ui.TextInput(
        label="Miniatura (esquina superior derecha)",
        placeholder="https://i.imgur.com/tu-icono.png",
        required=False,
        max_length=500,
    )
    url_imagen = discord.ui.TextInput(
        label="Banner grande (parte inferior del embed)",
        placeholder="https://i.imgur.com/tu-banner.png",
        required=False,
        max_length=500,
    )
    url_icono_autor = discord.ui.TextInput(
        label="Ícono del autor (junto al nombre del autor)",
        placeholder="https://i.imgur.com/tu-icono.png",
        required=False,
        max_length=500,
    )
    url_icono_pie = discord.ui.TextInput(
        label="Ícono del pie de página",
        placeholder="https://i.imgur.com/tu-icono.png",
        required=False,
        max_length=500,
    )

    def __init__(self, config_actual: dict):
        super().__init__()
        embed = config_actual.get("dm_embed", {})
        self.url_miniatura.default = embed.get("url_miniatura", "")
        self.url_imagen.default = embed.get("url_imagen", "")
        self.url_icono_autor.default = embed.get("url_icono_autor", "")
        self.url_icono_pie.default = embed.get("url_icono_pie", "")
        self._config = config_actual

    async def on_submit(self, interaction: discord.Interaction):
        embed_cfg = self._config.setdefault("dm_embed", {})

        embed_cfg["url_miniatura"] = self.url_miniatura.value
        embed_cfg["url_imagen"] = self.url_imagen.value
        embed_cfg["url_icono_autor"] = self.url_icono_autor.value
        embed_cfg["url_icono_pie"] = self.url_icono_pie.value

        guardar_config(self._config)
        interaction.client.config = self._config

        await interaction.response.send_message(
            "✅ **Imágenes del DM actualizadas.** Usa `/testdm` para previsualizarlas.",
            ephemeral=True,
        )
        log.info("Imágenes del embed de DM editadas por %s", interaction.user)


# ---------------------------------------------------------------------------
# Configuración del bot
# ---------------------------------------------------------------------------

# Intents — el intent de miembros es privilegiado y debe activarse
# manualmente en el Discord Developer Portal bajo "Privileged Gateway Intents".
intents = discord.Intents.default()
intents.members = True           # Necesario para on_member_join y member_count
intents.message_content = False  # No se necesita para comandos slash


class MichiganRPBot(commands.Bot):
    """Subclase personalizada del Bot que gestiona la config en tiempo real."""

    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)
        self.config: dict = {}

    async def setup_hook(self) -> None:
        """Se ejecuta una vez al iniciar sesión; sincroniza los comandos slash."""
        self.config = cargar_config()
        log.info("Configuración cargada.")
        await self.tree.sync()
        log.info("Comandos slash sincronizados.")

    async def on_ready(self) -> None:
        log.info("Conectado como %s (ID: %s)", self.user, self.user.id)
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name=self.config.get("mensaje_estado", "Michigan RP"),
            )
        )


bot = MichiganRPBot()


# ---------------------------------------------------------------------------
# Evento: on_member_join — se dispara cuando alguien entra al servidor
# ---------------------------------------------------------------------------

@bot.event
async def on_member_join(miembro: discord.Member) -> None:
    """
    Se activa cuando un nuevo miembro entra al servidor.
    1. Envía el embed de bienvenida al canal configurado.
    2. Intenta enviar el embed de bienvenida por DM al nuevo miembro.
    """
    cfg = bot.config

    # --- Embed en el canal de bienvenida ---------------------------------
    canal_id = cfg.get("welcome_channel_id")
    if canal_id:
        canal = miembro.guild.get_channel(int(canal_id))
        if canal:
            try:
                embed = construir_embed(cfg.get("welcome_embed", {}), miembro)
                await canal.send(content=miembro.mention, embed=embed)
                log.info("Embed de bienvenida enviado para %s en #%s", miembro, canal.name)
            except discord.Forbidden:
                log.warning("Sin permisos para enviar en el canal %s", canal_id)
            except Exception as error:
                log.error("Error al enviar embed de bienvenida: %s", error)
        else:
            log.warning("Canal de bienvenida con ID %s no encontrado.", canal_id)

    # --- Embed por DM ----------------------------------------------------
    try:
        embed_dm = construir_embed(cfg.get("dm_embed", {}), miembro)
        await miembro.send(embed=embed_dm)
        log.info("DM enviado a %s", miembro)
    except discord.Forbidden:
        # El usuario tiene los DMs desactivados — se registra y continúa
        log.info("No se pudo enviar DM a %s (DMs desactivados).", miembro)
    except Exception as error:
        log.error("Error inesperado al enviar DM a %s: %s", miembro, error)


# ---------------------------------------------------------------------------
# Comandos Slash
# ---------------------------------------------------------------------------

@bot.tree.command(name="testbienvenida", description="Envía un embed de bienvenida de prueba en el canal configurado.")
@app_commands.checks.has_permissions(manage_guild=True)
async def testbienvenida(interaction: discord.Interaction) -> None:
    """/testbienvenida — envía el embed de bienvenida al canal configurado como prueba."""
    cfg = bot.config
    canal_id = cfg.get("welcome_channel_id")

    if not canal_id:
        await interaction.response.send_message(
            "❌ No hay ningún `welcome_channel_id` configurado en config.json.", ephemeral=True
        )
        return

    canal = interaction.guild.get_channel(int(canal_id))
    if not canal:
        await interaction.response.send_message(
            f"❌ No se encontró el canal con ID `{canal_id}` en este servidor.", ephemeral=True
        )
        return

    try:
        embed = construir_embed(cfg.get("welcome_embed", {}), interaction.user)
        await canal.send(content=interaction.user.mention, embed=embed)
        await interaction.response.send_message(
            f"✅ Embed de bienvenida de prueba enviado en {canal.mention}.", ephemeral=True
        )
    except discord.Forbidden:
        await interaction.response.send_message(
            "❌ No tengo permiso para enviar mensajes en ese canal.", ephemeral=True
        )


@bot.tree.command(name="testdm", description="Te envía el embed de DM de bienvenida a ti mismo.")
async def testdm(interaction: discord.Interaction) -> None:
    """/testdm — envía el embed de DM directamente a quien ejecuta el comando."""
    cfg = bot.config

    try:
        embed_dm = construir_embed(cfg.get("dm_embed", {}), interaction.user)
        await interaction.user.send(embed=embed_dm)
        await interaction.response.send_message(
            "✅ DM de prueba enviado. ¡Revisa tus Mensajes Directos!", ephemeral=True
        )
    except discord.Forbidden:
        await interaction.response.send_message(
            "❌ No pude enviarte el DM. Activa los DMs de miembros del servidor en tu Configuración de Privacidad.",
            ephemeral=True,
        )


@bot.tree.command(name="editarbienvenida", description="Edita el mensaje embed del canal de bienvenida.")
@app_commands.checks.has_permissions(manage_guild=True)
async def editarbienvenida(interaction: discord.Interaction) -> None:
    """/editarbienvenida — abre un formulario para editar el embed del canal de bienvenida."""
    modal = ModalEditarBienvenida(bot.config)
    await interaction.response.send_modal(modal)


@bot.tree.command(name="editardm", description="Edita el mensaje embed que se envía por DM a nuevos miembros.")
@app_commands.checks.has_permissions(manage_guild=True)
async def editardm(interaction: discord.Interaction) -> None:
    """/editardm — abre un formulario para editar el embed de DM de bienvenida."""
    modal = ModalEditarDM(bot.config)
    await interaction.response.send_modal(modal)


@bot.tree.command(name="imagenesbienvenida", description="Edita las imágenes del embed del canal de bienvenida.")
@app_commands.checks.has_permissions(manage_guild=True)
async def imagenesbienvenida(interaction: discord.Interaction) -> None:
    """/imagenesbienvenida — abre un formulario para editar las URLs de imágenes del embed de bienvenida."""
    modal = ModalImagenesBienvenida(bot.config)
    await interaction.response.send_modal(modal)


@bot.tree.command(name="imagenesdm", description="Edita las imágenes del embed de DM de bienvenida.")
@app_commands.checks.has_permissions(manage_guild=True)
async def imagenesdm(interaction: discord.Interaction) -> None:
    """/imagenesdm — abre un formulario para editar las URLs de imágenes del embed de DM."""
    modal = ModalImagenesDM(bot.config)
    await interaction.response.send_modal(modal)


@bot.tree.command(name="setcanal", description="Selecciona el canal donde aparecerán los mensajes de bienvenida.")
@app_commands.checks.has_permissions(manage_guild=True)
@app_commands.describe(canal="Canal de texto donde se enviarán las bienvenidas")
async def setcanal(interaction: discord.Interaction, canal: discord.TextChannel) -> None:
    """/setcanal — guarda el canal de bienvenida sin tocar config.json manualmente."""
    bot.config["welcome_channel_id"] = str(canal.id)
    guardar_config(bot.config)

    await interaction.response.send_message(
        f"✅ Canal de bienvenida establecido en {canal.mention}.\n"
        f"Usa `/testbienvenida` para confirmar que todo se ve bien.",
        ephemeral=True,
    )
    log.info("Canal de bienvenida cambiado a #%s (%s) por %s", canal.name, canal.id, interaction.user)


@bot.tree.command(name="recargar", description="Recarga config.json sin reiniciar el bot.")
@app_commands.checks.has_permissions(manage_guild=True)
async def recargar(interaction: discord.Interaction) -> None:
    """/recargar — recarga config.json en tiempo real sin necesidad de reiniciar."""
    try:
        bot.config = cargar_config()
        log.info("Configuración recargada por %s", interaction.user)
        await interaction.response.send_message(
            "✅ `config.json` recargado correctamente.", ephemeral=True
        )
    except FileNotFoundError:
        await interaction.response.send_message(
            "❌ No se encontró `config.json`.", ephemeral=True
        )
    except json.JSONDecodeError as error:
        await interaction.response.send_message(
            f"❌ Error de formato JSON en `config.json`: `{error}`", ephemeral=True
        )


@bot.tree.command(name="ayuda", description="Muestra todos los comandos disponibles del bot.")
async def ayuda(interaction: discord.Interaction) -> None:
    """/ayuda — muestra una lista de todos los comandos disponibles."""
    embed = discord.Embed(
        title="📋 Comandos de Michigan RP Bot",
        description="Lista de todos los comandos disponibles:",
        color=discord.Color(0xE8A400),
        timestamp=datetime.now(timezone.utc),
    )
    embed.add_field(
        name="🔧 Administración (requiere Gestionar Servidor)",
        value=(
            "`/setcanal` — Selecciona el canal donde aparecen las bienvenidas\n"
            "`/testbienvenida` — Envía una prueba del embed de bienvenida al canal\n"
            "`/editarbienvenida` — Edita el texto del canal de bienvenida\n"
            "`/imagenesbienvenida` — Edita las imágenes del canal de bienvenida\n"
            "`/editardm` — Edita el texto del DM de bienvenida\n"
            "`/imagenesdm` — Edita las imágenes del DM de bienvenida\n"
            "`/recargar` — Recarga config.json sin reiniciar"
        ),
        inline=False,
    )
    embed.add_field(
        name="👤 Para todos",
        value=(
            "`/testdm` — Te envía el DM de bienvenida a ti mismo\n"
            "`/ayuda` — Muestra este mensaje"
        ),
        inline=False,
    )
    embed.add_field(
        name="📝 Variables disponibles en los mensajes",
        value="`{user}` `{username}` `{mention}` `{member_count}` `{server}`",
        inline=False,
    )
    embed.set_footer(text="Michigan RP Bot")
    await interaction.response.send_message(embed=embed, ephemeral=True)


# ---------------------------------------------------------------------------
# Manejador de errores de permisos para comandos de administración
# ---------------------------------------------------------------------------

@testbienvenida.error
@setcanal.error
@editarbienvenida.error
@imagenesbienvenida.error
@editardm.error
@imagenesdm.error
@recargar.error
async def error_permisos(
    interaction: discord.Interaction,
    error: app_commands.AppCommandError,
) -> None:
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message(
            "❌ Necesitas el permiso **Gestionar Servidor** para usar este comando.",
            ephemeral=True,
        )
    else:
        log.error("Error no manejado en comando: %s", error)
        await interaction.response.send_message(
            "❌ Ocurrió un error inesperado.", ephemeral=True
        )


# ---------------------------------------------------------------------------
# Punto de entrada
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # El token se lee desde la variable de entorno DISCORD_TOKEN.
    # Nunca escribas el token directamente en el código.
    token = os.environ.get("DISCORD_TOKEN")
    if not token:
        log.critical(
            "La variable de entorno DISCORD_TOKEN no está definida. "
            "Configúrala antes de iniciar el bot."
        )
        raise SystemExit(1)

    bot.run(token, log_handler=None)
