#!/usr/bin/env python3
"""
Visual NFA Form Filling for Rental Contract CPFs
Executes actual browser automation to fill NFA forms on ATF website
"""

import asyncio
import json
import sys
from datetime import datetime
from typing import Dict, Any, List

import httpx
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.panel import Panel
from rich.table import Table
from rich.live import Live
from rich import box

# Initialize Rich console
console = Console()

# CPFs from the rental contract data
RENTAL_CPFS = [
    "079.478.344-90",  # RN13 - Remessa por conta de contrato de locação
    "460.533.285-53",  # R003 - Remessa por conta de contrato de locação
]

# NFA Configuration
EMITENTE_CNPJ = "28.842.017/0001-05"
SOCKET_PATH = "/tmp/fbp.sock"
BASE_URL = "http://localhost"

# Credentials are intentionally NOT embedded in this file.
# FBP Backend reads them from its own environment (.env): NFA_USERNAME / NFA_PASSWORD.


async def _run_new_runner() -> None:
    from run_rental_nfa_batch import main as run_batch_main

    await run_batch_main()


if __name__ == "__main__":
    asyncio.run(_run_new_runner())


LEGACY_CODE = r'''

class NFACreator:
    def __init__(self):
        self.console = console
        self.jobs: List[Dict[str, Any]] = []
        
    def display_header(self):
        """Display application header."""
        header = Panel(
            "[bold cyan]🏢 NFA Visual Creator - Rental Contracts[/bold cyan]\n"
            f"[yellow]Date: {datetime.now().strftime('%B %d, %Y at %H:%M:%S')}[/yellow]\n"
            f"[green]Emitente CNPJ: {EMITENTE_CNPJ}[/green]\n"
            f"[blue]FBP Backend: Active on {SOCKET_PATH}[/blue]",
            title="[bold white]Sistema de Geração de NFA[/bold white]",
            border_style="bright_blue",
            box=box.DOUBLE
        )
        self.console.print(header)
        self.console.print()

    def create_nfa_payload(self, cpf: str, index: int) -> Dict[str, Any]:
        """Create NFA form-filling payload for browser automation."""
        clean_cpf = cpf.replace(".", "").replace("-", "")
        
        # Calculate service value based on CPF index
        base_value = 1500 + index * 250
        
        payload = {
            "emitente": {
                "cnpj": EMITENTE_CNPJ.replace(".", "").replace("/", "").replace("-", ""),
                "razao_social": "EMPRESA LOCADORA AUTOGIO LTDA",
                "nome_fantasia": "AUTOGIO LOCACOES",
                "inscricao_municipal": "123456789",
                "endereco": {
                    "logradouro": "RUA DAS LOCACOES",
                    "numero": "1000",
                    "bairro": "CENTRO EMPRESARIAL", 
                    "cidade": "SAO PAULO",
                    "uf": "SP",
                    "cep": "01000000"
                }
            },
            "destinatario": {
                "cpf": clean_cpf,
                "nome": f"LOCATARIO {index:02d} - CPF {cpf}",
                "endereco": {
                    "logradouro": f"RUA DO LOCATARIO {index:02d}",
                    "numero": f"{400 + index * 10}",
                    "bairro": "VILA MADALENA",
                    "cidade": "SAO PAULO",
                    "uf": "SP", 
                    "cep": "05433000"
                }
            },
            "produtos": [{
                "descricao": "Remessa por conta de contrato de locação",
                "valor_unitario": f"{base_value}.00",
                "quantidade": "1",
                "valor_total": f"{base_value}.00"
            }],
            "natureza_operacao": "Prestação de serviços",
            "motivo": "Contrato de locação",
            "cfop": "5933",  # Prestação de serviço sujeita ao ISSQN
            "informacoes_adicionais": f"NFA referente a contrato de locação - CPF {cpf} - Período: {datetime.now().strftime('%m/%Y')}",
            "credentials": {
                "usernform-filling automation to FBP Backend."""
        payload = self.create_nfa_payload(cpf, index)
        
        try:
            async with httpx.AsyncClient(
                transport=httpx.AsyncHTTPTransport(uds=SOCKET_PATH),
                timeout=120.0  # Extended timeout for form filling
            ) as client:
                
                self.console.print(f"[yellow]🌐 Starting browser automation for CPF {cpf}...[/yellow]")
                self.console.print(f"[dim]   Opening ATF website and filling NFA form...[/dim]")
                
                # Use n8n NFA endpoint for actual form filling
                response = await client.post(
                    f"{BASE_URL}/api/nfa/create",
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )
                
                if response.status_code == 200:
                    result = response.json()
                    
                    if result.get("success"):
                        data = result.get("data", {})
                        self.console.print(f"[green]✅ NFA form filled successfully for CPF {cpf}[/green]")
                        self.console.print(f"[dim]   NFA Number: {data.get('nfa_number', 'Generated')}[/dim]")
                        self.console.print(f"[dim]   Status: {data.get('status', 'Completed')}[/dim]")
                        
                        return {
                            "cpf": cpf,
                            "success": True,
                            "nfa_number": data.get("nfa_number"),
                            "status": data.get("status", "completed"),
                            "screenshot_path": data.get("screenshot_path"),
                            "payload": payload,
                            "data": data
                        }
                    else:
                        errors = result.get("errors", ["Unknown error"])
                        error_msg = "; ".join(errors)
                        self.console.print(f"[red]❌ NFA automation failed for CPF {cpf}[/red]")
                        self.console.print(f"[dim]   Errors: {error_msg}[/dim]")
                        
                        return {
                            "cpf": cpf,
                            "success": False,
                            "error": error_msg,
                            "payload": payload
                        }
                else:
                    error_text = response.text
                    self.console.print(f"[red]❌ HTTP Error {response.status_code} for CPF {cpf}[/red]")
                    self.console.print(f"[dim]   Response: {error_text}[/dim]")
                    return {
                        "cpf": cpf,
                        "success": False,
                        "error": f"HTTP {response.status_code}: {error_text}",
                        "payload": payload
                    }
                    
        except Exception as e:
            self.console.print(f"[red]❌ Browser automation failed for CPF {cpf}: {str(e)}[/red]")
            return {
                "cpf": cpf,
                "success": False,
                "error": str(e),
                "payload": payload
            }
                    
        except Exception as e:
            self.console.print(f"[red]❌ Exception for CPF {cpf}: {str(e)}[/red]")
            return {
                "cpf": cpf,
                "success": False,
                "error": str(e),
                "payload": payload
            }

    async def check_job_status(self, job_id: str) -> Dict[str, Any]:
        """Check NFA job status."""
        try:
            async with httpx.AsyncClient(
                transport=httpx.AsyncHTTPTransport(uds=SOCKET_PATH),
                timeout=30.0
            ) as client:
                
                response = await client.get(f"{BASE_URL}/nfa/status/{job_id}")
                
                if response.status_code == 200:
                    return response.json()
                else:
                    return {
                        "error": f"HTTP {response.status_code}: {response.text}",
                        "job_id": job_id
                    }
                    
        except Exception as e:
            return {"error": str(e), "job_id": job_id}

    def display_summary_table(self):
        """Display summary table of all operations."""
        table = Table(title="[bold]🌐 NFA Form Automation Summary[/bold]", box=box.ROUNDED)
        table.add_column("CPF", style="cyan", no_wrap=True)
        table.add_column("Status", style="bold")
        table.add_column("NFA Number", style="dim")
        table.add_column("Value", style="green") 
        table.add_column("Form Details")
        
        for job in self.jobs:
            if job['success']:
                status = "[green]✅ FORM FILLED[/green]"
                nfa_number = job.get('nfa_number', 'Generated')
                value = f"R$ {job['payload']['produtos'][0]['valor_total']}"
                details = f"Service: {job['payload']['produtos'][0]['descricao'][:25]}..."
            else:
                status = "[red]❌ FORM FAILED[/red]"
                nfa_number = "N/A"
                value = f"R$ {job['payload']['produtos'][0]['valor_total']}"
                details = f"Error: {job['error'][:30]}..."
                
            table.add_row(
                job['cpf'],
                status,
                nfa_number,
                value,
                details
            )
        
        self.console.print(table)

    async def run(self):
        """Execute the complete NFA creation process."""
        self.display_header()
        
        # Display target information
        target_panel = Panel(
            f"[bold yellow]🎯 Browser Automation - NFA Form Filling:[/bold yellow]\n" +
            "\n".join([f"[cyan]• {cpf}[/cyan] - ATF Website Form Automation" for cpf in RENTAL_CPFS]) +
            f"\n\n[blue]🌐 Process:[/blue]\n" +
            f"[dim]• Login to ATF website ({NFA_USERNAME})[/dim]\n" +
            f"[dim]• Navigate to NFA creation form[/dim]\n" +
            f"[dim]• Fill all required fields automatically[/dim]\n" +
            f"[dim]• Submit form and capture results[/dim]",
            title="Browser Automation Process",
            border_style="yellow"
        )
        self.console.print(target_panel)
        self.console.print()

        # Create progress bar
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=self.console
        ) as progress:
            
            task = progress.add_task("Creating NFAs...", total=len(RENTAL_CPFS))
            
            # Process each CPF
            for i, cpf in enumerate(RENTAL_CPFS, 1):
                progress.update(task, description=f"Processing CPF {cpf} ({i}/{len(RENTAL_CPFS)})")
                
                result = await self.submit_nfa(cpf, i)
                self.jobs.append(result)
                
                progress.advance(task)
                
                # Small delay for visual effect
                await asyncio.sleep(1)
        
        self.console.print()
        
        # Display results
        self.display_summary_table()
        
        # Display screenshots and results for successful submissions
        successful_jobs = [job for job in self.jobs if job['success']]
        
        if successful_jobs:
            self.console.print()
            self.console.print("[bold blue]📋 Form Filling Results:[/bold blue]")
            
            for job in successful_jobs:
                cpf = job['cpf']
                nfa_number = job.get('nfa_number', 'Generated')
                screenshot = job.get('screenshot_path', 'N/A')
                
                self.console.print(f"[green]✅ CPF {cpf}:[/green]")
                self.console.print(f"[dim]   NFA Number: {nfa_number}[/dim]")
                self.console.print(f"[dim]   Screenshot: {screenshot}[/dim]")
                self.console.print(f"[dim]   Form Status: Submitted Successfully[/dim]")
        
        # Final summary
        successful_count = len(successful_jobs)
        failed_count = len(self.jobs) - successful_count
        
        final_panel = Panel(
            f"[bold green]🎉 Process Completed![/bold green]\n\n"
            f"[green]✅ Successful NFAs: {successful_count}[/green]\n"
            f"[red]❌ Failed NFAs: {failed_count}[/red]\n"
            f"[blue]📊 Total Processed: {len(self.jobs)}[/blue]\n\n"
            f"[yellow]💡 Next Steps:[/yellow]\n"
            f"• Check NFA status in FBP Backend logs\n"
            f"• Monitor job completion via status endpoints\n"
            f"• Download generated PDFs when ready",
            title="[bold white]Execution Summary[/bold white]",
            border_style="green",
            box=box.DOUBLE
        )
        
        self.console.print()
        self.console.print(final_panel)

async def main():
    """Main execution function."""
    try:browser screenshots in output directory\n"
            f"• Verify NFA numbers in ATF system\n"
            f"• Download NFAs from ATF portal if needed\n"
            f"• Review form data in FBP Backend logs
    except KeyboardInterrupt:
        console.print("\n[yellow]⚠️  Process interrupted by user[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n[red]❌ Unexpected error: {e}[/red]")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
'''