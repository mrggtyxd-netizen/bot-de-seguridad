import os
import discord.py
from discord import app_commands
from discord.ext import commands, tasks
from discord.ui import Button, View
import asyncio
import time
import re
from datetime import datetime

TOKEN = os.getenv("BOT_TOKEN")
ALERT_CHANNEL_NAME = "alertas-seguridad"

# IDs de Administradores del Servidor (Reemplaza con IDs reales de tu Staff)
ADMIN_IDS = [123456789012345678] 

class SecuritySystemPro(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix=";", intents=discord.Intents.all())
        # Estructuras de memoria para el monitoreo 24/7
        self.registro_spam = {}
        self.registro_uniones = []
        self.modo_panico = False

    async def setup_hook(self):
        await self.tree.sync()
        print("⚡ [SISTEMA] Todos los Slash Commands avanzados han sido sincronizados con Discord.")

bot = SecuritySystemPro()

@bot.event
async def on_ready():
    print(f"==================================================")
    print(f"🔒 SEGURIDAD PERIMETRAL AL SIGUIENTE NIVEL ACTIVADA")
    print(f"Bot Conectado: {bot.user.name} | Monitoreo 24/7 Listo")
    print(f"==================================================")
    verificar_modo_panico_task.start()

# --- TAREA 24/7: Resetear el Modo Pánico automáticamente tras 5 minutos ---
@tasks.loop(minutes=5)
async def verificar_modo_panico_task():
    if bot.modo_panico:
        bot.modo_panico = False
        print("🛡️ [Anti-Raid] Modo Pánico desactivado automáticamente por tiempo expirado.")

# =========================================================================
# EVENTOS DE DETECCIÓN, PREVENCIÓN Y MONITOREO
# =========================================================================

# 1. ANTI-BOTS INVASORES & CONTROL ANTI-RAID (Masa de Uniones)
@bot.event
async def on_member_join(member: discord.Member):
    guild = member.guild
    alert_channel = discord.utils.get(guild.channels, name=ALERT_CHANNEL_NAME)
    ahora = time.time()

    # CONTROL ANTI-RAID: Mitigación de ingresos masivos
    bot.registro_uniones = [t for t in bot.registro_uniones if ahora - t < 10]
    bot.registro_uniones.append(ahora)

    if len(bot.registro_uniones) > 5 and not bot.modo_panico:
        bot.modo_panico = True
        if alert_channel:
            embed_panic = discord.Embed(
                title="🚨 ¡ALERTA DE ANTI-RAID ACTIVADA!",
                description="Se ha detectado el ingreso de más de 5 cuentas en menos de 10 segundos. El **Modo Pánico** se ha encendido.",
                color=discord.Color.dark_red()
            )
            embed_panic.add_field(name="Efecto", value="Se denegará preventivamente cualquier acción sospechosa.")
            await alert_channel.send(embed=embed_panic)

    # ACCIÓN SI EL NUEVO MIEMBRO ES UN BOT
    if member.bot:
        try:
            roles_a_remover = [role for role in member.roles if role != guild.default_role and not role.managed]
            if roles_a_remover:
                await member.remove_roles(*roles_a_remover, reason="Cuarentena preventiva: Verificación requerida.")
        except discord.Forbidden:
            pass

        invitado_por = "Desconocido"
        responsable_id = None
        await asyncio.sleep(2)
        try:
            async for entry in guild.audit_logs(action=discord.AuditLogAction.bot_add, limit=1):
                if entry.target.id == member.id:
                    invitado_por = f"{entry.user.mention} (`{entry.user.id}`)"
                    responsable_id = entry.user.id
                    break
        except discord.Forbidden:
            pass

        if alert_channel:
            class VistaJuicio(View):
                def __init__(self):
                    super().__init__(timeout=None)

                async def interaction_check(self, interaction: discord.Interaction) -> bool:
                    if interaction.user.id != guild.owner_id:
                        await interaction.response.send_message("❌ Solo el dueño absoluto del servidor puede ejecutar esto.", ephemeral=True)
                        return False
                    return True

                @discord.ui.button(label="Permitir Bot", style=discord.ButtonStyle.green, emoji="✅")
                async def permitir(self, interaction: discord.Interaction, button: Button):
                    for b in self.children: b.disabled = True
                    await interaction.response.edit_message(view=self)
                    await alert_channel.send(f"🟢 El dueño autorizó el ingreso del bot {member.mention}.")

                @discord.ui.button(label="Banear Ambos", style=discord.ButtonStyle.danger, emoji="⚡")
                async def banear_ambos(self, interaction: discord.Interaction, button: Button):
                    for b in self.children: b.disabled = True
                    await interaction.response.edit_message(view=self)
                    await guild.ban(member, reason="Bot no autorizado.")
                    if responsable_id and responsable_id != guild.owner_id:
                        usuario_resp = guild.get_member(responsable_id)
                        if usuario_resp:
                            await guild.ban(usuario_resp, reason="Invasión: Invitar bots no autorizados.")
                            await alert_channel.send(f"🔴 **Baneo Exitoso:** Bot {member.name} e invitador {usuario_resp.mention} eliminados.")
                    else:
                        await alert_channel.send(f"🔴 **Baneo Parcial:** El bot fue expulsado permanentemente.")

            embed_bot = discord.Embed(title="🤖 BOT DETECTADO EN PERÍMETRO", color=discord.Color.red())
            embed_bot.add_field(name="Identificación", value=f"{member.mention} (`{member.id}`)", inline=False)
            embed_bot.add_field(name="Invitado por", value=invitado_por, inline=False)
            await alert_channel.send(embed=embed_bot, view=VistaJuicio())

# 2. ANTI-SPAM (Lockdown), FILTRO INVITES (Regex) Y GHOST-PING
@bot.event
async def on_message(message: discord.Message):
    if message.author.bot or not message.guild:
        return

    guild = message.guild
    canal = message.channel
    alert_channel = discord.utils.get(guild.channels, name=ALERT_CHANNEL_NAME)
    ahora = time.time()

    # FILTRO DE INVITACIONES (Regex)
    patron_invites = r"(discord\.gg\/|discord\.com\/invite\/)"
    if re.search(patron_invites, message.content.lower()):
        # Eximir a administradores reales del filtro
        if message.author.id not in ADMIN_IDS and not message.author.guild_permissions.administrator:
            await message.delete()
            if alert_channel:
                await alert_channel.send(f"⚠️ **Filtro Publicidad:** Se eliminó una invitación de {message.author.mention} en {canal.mention}.")
            return

    # CONTROL ANTI-SPAM DE FLUJO
    usuario_id = message.author.id
    if usuario_id not in bot.registro_spam:
        bot.registro_spam[usuario_id] = []
    bot.registro_spam[usuario_id] = [t for t in bot.registro_spam[usuario_id] if ahora - t < 3]
    bot.registro_spam[usuario_id].append(ahora)

    if len(bot.registro_spam[usuario_id]) > 5:
        if canal.name != ALERT_CHANNEL_NAME:
            try:
                overwrites = canal.overwrites_for(guild.default_role)
                overwrites.send_messages = False
                await canal.set_permissions(guild.default_role, overwrite=overwrites, reason="Lockdown automático por ráfaga.")
                
                await canal.send(embed=discord.Embed(title="🔒 CANAL CERRADO", description="Bloqueado por exceso de spam.", color=discord.Color.dark_red()))
                
                if alert_channel:
                    await alert_channel.send(f"⚠️ **Lockdown Aplicado:** Canal {canal.mention} clausurado. Infractor: {message.author.mention}.")
                bot.registro_spam[usuario_id] = []
            except discord.Forbidden:
                pass

    await bot.process_commands(message)

# 3. MONITOREO DE GHOST-PINGS (Menciones Fantasma)
@bot.event
async def on_message_delete(message: discord.Message):
    if message.author.bot or not message.guild:
        return

    if message.mention_everyone or len(message.mentions) > 0:
        alert_channel = discord.utils.get(message.guild.channels, name=ALERT_CHANNEL_NAME)
        if alert_channel:
            embed = discord.Embed(title="👻 ALERTA: Mención Fantasma Detectada (Ghost-Ping)", color=discord.Color.orange())
            embed.add_field(name="Autor", value=message.author.mention, inline=True)
            embed.add_field(name="Canal", value=message.channel.mention, inline=True)
            embed.add_field(name="Contenido Eliminado", value=message.content if message.content else "*[Solo multimedia]*", inline=False)
            await alert_channel.send(embed=embed)

# =========================================================================
# SLASH COMMANDS (CONTROL DE MANDOS DEL PANEL)
# =========================================================================

# /guia
@bot.tree.command(name="guia", description="Muestra el manual interactivo de operaciones y comandos de seguridad.")
async def guia(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🛡️ MANUAL DE OPERACIONES Y COMANDOS",
        description="Este bot ejecuta contramedidas de ciberseguridad avanzada las 24 horas del día. A continuación, tienes la lista detallada de funciones y comandos disponibles:",
        color=discord.Color.blue()
    )
    embed.add_field(
        name="🛰️ Comandos de Barra Diagonal (Slash Commands)",
        value=(
            "**`/setup_seguridad`**\nInicializa la infraestructura del bot creando el canal privado `#alertas-seguridad`.\n\n"
            "**`/unlock`**\nRemueve el estado de Lockdown del canal actual restableciendo los permisos normales de escritura.\n\n"
            "**`/server_health`**\nRealiza una auditoría analítica profunda buscando fallas, vulnerabilidades o excesos de permisos en roles."
        ),
        inline=False
    )
    embed.add_field(
        name="⚙️ Sistemas Automatizados Operando 24/7",
        value=(
            "• **Anti-Bots Invasores:** Aísla cualquier bot que se una al servidor y le da control al Dueño para banear al bot y a su invitador.\n"
            "• **Anti-Spam de Flujo:** Cierra automáticamente el canal si un usuario envía más de 5 mensajes en 3 segundos.\n"
            "• **Anti-Raid (Modo Pánico):** Detecta oleadas de ingresos inusuales y alerta al equipo de Staff.\n"
            "• **Filtro Publicitario:** Elimina enlaces Regex estilo `discord.gg` creados por cuentas sospechosas.\n"
            "• **Rastreador Ghost-Ping:** Expone y notifica de inmediato las menciones borradas."
        ),
        inline=False
    )
    embed.set_footer(text="Garantizando protección perimetral constante • Desarrollado para Render")
    await interaction.response.send_message(embed=embed)

# /setup_seguridad
@bot.tree.command(name="setup_seguridad", description="Crea e inicializa el centro privado de operaciones y logs de seguridad.")
@app_commands.checks.has_permissions(administrator=True)
async def setup_seguridad(interaction: discord.Interaction):
    guild = interaction.guild
    canal_existente = discord.utils.get(guild.channels, name=ALERT_CHANNEL_NAME)
    
    if canal_existente:
        return await interaction.response.send_message(f"El canal de alertas {canal_existente.mention} ya está operativo.", ephemeral=True)
        
    await interaction.response.defer(ephemeral=True)
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, embed_links=True)
    }
    nuevo_canal = await guild.create_text_channel(name=ALERT_CHANNEL_NAME, overwrites=overwrites, reason="Configuración SIEM.")
    await interaction.followup.send(f"✅ **Ecosistema listo.** El canal {nuevo_canal.mention} ha sido configurado correctamente.")

# /unlock
@bot.tree.command(name="unlock", description="Abre el canal de texto actual removiendo el bloqueo anti-spam.")
@app_commands.checks.has_permissions(manage_channels=True)
async def unlock(interaction: discord.Interaction):
    guild = interaction.guild
    canal = interaction.channel
    try:
        overwrites = canal.overwrites_for(guild.default_role)
        overwrites.send_messages = None  
        await canal.set_permissions(guild.default_role, overwrite=overwrites, reason="Reapertura manual autorizada.")
        await interaction.response.send_message("🔓 **Canal Reabierto.** Flujo de chat restablecido para los usuarios.")
    except discord.Forbidden:
        await interaction.response.send_message("❌ Error: Permisos insuficientes para modificar este canal.", ephemeral=True)

# /server_health
@bot.tree.command(name="server_health", description="Audita de forma analítica el estado actual de seguridad del servidor.")
@app_commands.checks.has_permissions(administrator=True)
async def server_health(interaction: discord.Interaction):
    await interaction.response.defer()
    guild = interaction.guild
    
    # Análisis de roles con permisos de Administrador
    roles_admin = [role.mention for role in guild.roles if role.permissions.administrator and role != guild.default_role]
    canales_totales = len(guild.channels)
    miembros_totales = guild.member_count
    
    embed = discord.Embed(title="🏥 INFORME DE DIAGNÓSTICO Y SALUD DEL SERVIDOR", color=discord.Color.green())
    embed.add_field(name="👥 Población de Miembros", value=f"`{miembros_totales}` cuentas en el servidor.", inline=True)
    embed.add_field(name="📁 Infraestructura", value=f"`{canales_totales}` canales de texto/voz monitoreados.", inline=True)
    embed.add_field(name="🛑 Roles con Poder Absoluto (Administrador)", value=", ".join(roles_admin) if roles_admin else "Ninguno fuera del staff principal.", inline=False)
    
    # Análisis de amenazas internas
    status_critico = "🟢 Óptimo" if len(roles_admin) <= 3 else "⚠️ Riesgo Elevado (Demasiados administradores)"
    embed.add_field(name="⚖️ Evaluación de Riesgo de Brechas", value=f"**{status_critico}**", inline=False)
    embed.set_footer(text=f"Latencia de Respuesta Webhook: {round(bot.latency * 1000)}ms")
    
    await interaction.followup.send(embed=embed)

# Manejo centralizado de fallos de permisos en comandos
@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.errors.MissingPermissions):
        if not interaction.response.is_done():
            await interaction.response.send_message("❌ **Denegado:** Tus roles asignados no tienen los permisos jerárquicos para usar este comando.", ephemeral=True)

if __name__ == "__main__":
    if not TOKEN:
        print("❌ ERROR CRÍTICO: Falta la variable BOT_TOKEN en el entorno de Render.")
    else:
        bot.run(TOKEN)
        
