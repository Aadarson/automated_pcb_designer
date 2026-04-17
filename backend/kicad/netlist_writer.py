import logging

logger = logging.getLogger(__name__)

def write_netlist(job_id: str, request, output_path: str):
    logger.info(f"Writing Netlist to {output_path}")
    with open(output_path, "w") as f:
        f.write("(export (version D)\n")
        f.write(")\n")
