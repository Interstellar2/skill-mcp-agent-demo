export function bindGraphEvents(cy: cytoscape.Core): void {
  // Hover effects
  cy.on('mouseover', 'node', (evt) => {
    evt.target.addClass('hover')
  })
  cy.on('mouseout', 'node', (evt) => {
    evt.target.removeClass('hover')
  })

  // Click node to center
  cy.on('tap', 'node', (evt) => {
    cy.animate({
      fit: { eles: evt.target, padding: 80 },
      duration: 300,
    })
  })

  // Double-click blank area to reset fit
  cy.on('tap', (evt) => {
    if (evt.target === cy) {
      cy.animate({
        fit: { eles: cy.elements(), padding: 40 },
        duration: 350,
      })
    }
  })

  // Auto-fit on initial layout
  cy.one('layoutstop', () => {
    cy.fit(cy.elements(), 40)
  })
}

export function createResizeObserver(cy: cytoscape.Core, container: HTMLElement): ResizeObserver {
  const resizeObserver = new ResizeObserver(() => {
    cy.resize()
    cy.fit(cy.elements(), 40)
  })
  resizeObserver.observe(container)
  return resizeObserver
}
